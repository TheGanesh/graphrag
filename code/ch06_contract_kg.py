"""Chapter 6 - build a knowledge graph from contracts with LLM structured outputs.

    python ch06_contract_kg.py                         # uses data/sample_contract.txt
    python ch06_contract_kg.py path/to/contract.txt    # e.g. a CUAD contract

contract text -> LLM + Pydantic schema (Structured Outputs) -> JSON
             -> AQL UPSERT into   organizations --has_party{role}--> contracts
                                  organizations --located_at-->     locations
                                  contracts     --has_chunk-->      contract_chunks
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
from typing import Literal, Optional

from pydantic import BaseModel, Field

from kit import db as kdb
from kit import llm
from kit.text import chunk_text, content_key

DB_NAME = "ch06"
HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------- schema
class Location(BaseModel):
    """A physical location: street address, city, state or region, and country."""
    address: Optional[str] = Field(..., description="Street address, if stated.")
    city: Optional[str] = Field(..., description="City, if stated.")
    state: Optional[str] = Field(..., description="State or region, if stated.")
    country: str = Field(..., description="Country as a two-letter ISO 3166 code, e.g. US, GB.")


class Organization(BaseModel):
    """An organization that is a party to the contract."""
    name: str = Field(..., description="The organization's name as written in the contract.")
    location: Location = Field(..., description="The organization's primary location.")
    role: str = Field(..., description="Its role in the contract, e.g. 'provider', 'client', "
                                       "'licensor', 'licensee', 'supplier'.")


class Contract(BaseModel):
    """The key facts of a contract."""
    contract_type: Literal["Service Agreement", "Licensing Agreement",
                           "Non-Disclosure Agreement (NDA)", "Partnership Agreement",
                           "Lease Agreement"] = Field(..., description="The kind of contract.")
    parties: list[Organization] = Field(..., description="All parties, with their roles.")
    effective_date: str = Field(..., description="When the contract takes effect, yyyy-MM-dd.")
    term: str = Field(..., description="Duration, including renewal or termination provisions.")
    contract_scope: str = Field(..., description="Scope: rights, duties and limitations.")
    end_date: Optional[str] = Field(..., description="When the contract expires, yyyy-MM-dd, if stated.")
    total_amount: Optional[float] = Field(..., description="Total contract value, if stated.")
    governing_law: Optional[Location] = Field(..., description="Jurisdiction whose law governs the contract.")


SYSTEM_MESSAGE = """You extract structured facts from legal contracts.
Identify the parties and their roles, the key dates, the term, the scope and the
governing law. Be concise: skip boilerplate. If a fact is not in the contract,
leave it empty rather than guessing. The output feeds a database that answers
questions about the company's contracts."""


def extract(document: str) -> dict:
    contract = llm.parse([{"role": "system", "content": SYSTEM_MESSAGE},
                          {"role": "user", "content": document}], Contract)
    return contract.model_dump()


# --------------------------------------------------------------------------- AQL
# Book listing 6.13 in AQL. Differences on purpose:
#  * the contract key is derived from the document text, so re-importing the same
#    contract updates it instead of creating a duplicate (the book's randomUUID()
#    version is not idempotent);
#  * CONCAT_SEPARATOR skips null parts, so a missing street address does not turn
#    the whole full_address into null.
IMPORT_CONTRACT = """
LET c = @contract
LET contract = FIRST(
  INSERT {
    _key: @contract_key,
    contract_type: c.contract_type,
    effective_date: c.effective_date,
    end_date: c.end_date,
    term: c.term,
    contract_scope: c.contract_scope,
    total_amount: c.total_amount,
    governing_law: c.governing_law == null ? null
                   : CONCAT_SEPARATOR(", ", c.governing_law.state, c.governing_law.country)
  } INTO contracts OPTIONS { overwriteMode: "replace" }
  RETURN NEW
)
LET orgs = (
  FOR party IN c.parties
    UPSERT { name: party.name }
    INSERT { name: party.name }
    UPDATE {}
    IN organizations
    RETURN { org: NEW, party }
)
LET placed = (
  FOR o IN orgs
    LET loc = o.party.location
    LET full_address = CONCAT_SEPARATOR(", ", loc.address, loc.city, loc.state, loc.country)
    UPSERT { full_address: full_address }
    INSERT MERGE(loc, { full_address: full_address })
    UPDATE {}
    IN locations
    RETURN { org: o.org, location: NEW, role: o.party.role }
)
LET located = (
  FOR p IN placed
    UPSERT { _from: p.org._id, _to: p.location._id }
    INSERT { _from: p.org._id, _to: p.location._id }
    UPDATE {}
    IN located_at
    RETURN NEW._id
)
FOR p IN placed
  UPSERT { _from: p.org._id, _to: contract._id }
  INSERT { _from: p.org._id, _to: contract._id, role: p.role }
  UPDATE { role: p.role }
  IN has_party
  RETURN { contract: contract._key, party: p.org.name, role: p.role }
"""

IMPORT_CHUNKS = """
LET kids = (
  FOR i IN 0..LENGTH(@texts) - 1
    INSERT { _key: CONCAT(@contract_key, "-", i), text: @texts[i], embedding: @embeddings[i] }
    INTO contract_chunks OPTIONS { overwriteMode: "replace" }
    RETURN NEW._id
)
FOR kid IN kids
  INSERT { _key: PARSE_IDENTIFIER(kid).key, _from: CONCAT("contracts/", @contract_key), _to: kid }
  INTO has_chunk OPTIONS { overwriteMode: "ignore" }
"""

# Figure 6.1's problem, solved: narrow down with the graph (which contract?),
# *then* rank only that contract's chunks by similarity (exact cosine, few rows).
CONTRACT_SCOPED_SEARCH = """
FOR org IN organizations
  FILTER CONTAINS(LOWER(org.name), LOWER(@party))
  FOR contract IN 1..1 OUTBOUND org has_party
    FOR chunk IN 1..1 OUTBOUND contract has_chunk
      LET score = COSINE_SIMILARITY(chunk.embedding, @question_embedding)
      SORT score DESC
      LIMIT @k
      RETURN { contract: contract._key, text: chunk.text, score }
"""

# A BI-style question that embeddings cannot answer: filter + count.
ACTIVE_CONTRACTS_WITH = """
FOR org IN organizations
  FILTER CONTAINS(LOWER(org.name), LOWER(@party))
  FOR contract IN 1..1 OUTBOUND org has_party
    FILTER contract.end_date == null OR contract.end_date >= @today
    COLLECT WITH COUNT INTO active_contracts
    RETURN active_contracts
"""

# Entity resolution, step 1: names that collapse to the same normalized form.
DUPLICATE_CANDIDATES = """
FOR o IN organizations
  LET normalized = TRIM(REGEX_REPLACE(REGEX_REPLACE(LOWER(o.name), @noise, ""), " +", " "))
  COLLECT canonical = normalized INTO group = { key: o._key, name: o.name }
  FILTER LENGTH(group) > 1
  RETURN { canonical, organizations: group }
"""
LEGAL_NOISE = r"[.,]|\b(incorporated|inc|corporation|corp|company|co|limited|ltd|llc|plc|gmbh)\b"

# Entity resolution, step 1b: near-misses (typos) by edit distance. O(n^2): fine
# for thousands of names; use an ArangoSearch n-gram view for millions.
FUZZY_CANDIDATES = """
FOR a IN organizations
  FOR b IN organizations
    FILTER a._key < b._key
    LET distance = LEVENSHTEIN_DISTANCE(LOWER(a.name), LOWER(b.name))
    FILTER distance <= @max_distance
    RETURN { a: a.name, b: b.name, distance }
"""

# Entity resolution, step 2: point every edge at the survivor, then drop the rest.
# (_from/_to are mutable in ArangoDB, so this is a plain UPDATE.)
REPOINT_PARTIES = """
LET keep = CONCAT("organizations/", @keep_key)
LET dupes = (FOR k IN @duplicate_keys RETURN CONCAT("organizations/", k))
FOR e IN has_party
  FILTER e._from IN dupes
  UPDATE e WITH { _from: keep } IN has_party
"""
REPOINT_LOCATIONS = REPOINT_PARTIES.replace("has_party", "located_at")
REMOVE_DUPLICATES = """
FOR k IN @duplicate_keys
  REMOVE k IN organizations
"""


def setup(db) -> None:
    kdb.ensure_graph(db, "contracts", [
        {"edge_collection": "has_party", "from_vertex_collections": ["organizations"],
         "to_vertex_collections": ["contracts"]},
        {"edge_collection": "located_at", "from_vertex_collections": ["organizations"],
         "to_vertex_collections": ["locations"]},
        {"edge_collection": "has_chunk", "from_vertex_collections": ["contracts"],
         "to_vertex_collections": ["contract_chunks"]},
    ])
    # the "unique constraints" of listing 6.12 are unique persistent indexes here
    kdb.ensure_persistent_index(db.collection("organizations"), ["name"], unique=True)
    kdb.ensure_persistent_index(db.collection("locations"), ["full_address"], unique=True)


def import_contract(db, data: dict, document: str) -> list[dict]:
    return kdb.aql(db, IMPORT_CONTRACT, contract=data, contract_key=content_key(document))


def split_into_clauses(document: str) -> list[str]:
    """Legal text reads best clause by clause: split before '1.', '2.3', 'ARTICLE', 'SECTION'."""
    parts = re.split(r"\n(?=\s*(?:\d+(?:\.\d+)*\.?\s+[A-Z]|ARTICLE\s|SECTION\s))", document)
    clauses = [p.strip() for p in parts if p.strip()]
    if len(clauses) < 3:                      # no visible structure: fall back to windows
        clauses = chunk_text(document, 1500, 100)
    return clauses


def add_chunks(db, document: str) -> int:
    texts = split_into_clauses(document)
    embeddings = llm.embed(texts)
    kdb.aql(db, IMPORT_CHUNKS, contract_key=content_key(document), texts=texts, embeddings=embeddings)
    return len(texts)


def merge_organizations(db, keep_key: str, duplicate_keys: list[str]) -> None:
    for q in (REPOINT_PARTIES, REPOINT_LOCATIONS):
        kdb.aql(db, q, keep_key=keep_key, duplicate_keys=duplicate_keys)
    kdb.aql(db, REMOVE_DUPLICATES, duplicate_keys=duplicate_keys)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "data", "sample_contract.txt")
    document = open(path, encoding="utf-8").read()
    db = kdb.connect(DB_NAME)
    setup(db)
    data = extract(document)
    print(json.dumps(data, indent=2))
    print(import_contract(db, data, document))
    print("chunks:", add_chunks(db, document))
    print("duplicate candidates:", kdb.aql(db, DUPLICATE_CANDIDATES, noise=LEGAL_NOISE))
    party = data["parties"][0]["name"]
    print(f"active contracts with {party}:",
          kdb.aql(db, ACTIVE_CONTRACTS_WITH, party=party, today=datetime.date.today().isoformat()))
    q = "What are the payment terms?"
    print(kdb.aql(db, CONTRACT_SCOPED_SEARCH, party=party, question_embedding=llm.embed([q])[0], k=2))


if __name__ == "__main__":
    main()
