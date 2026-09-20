#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Legal Integrity Verification & Anti-Hallucination Audit Tool
============================================================
Cryptographically verifies that every statute in `thai_law.db` matches
its raw source file in `raw_sources/` byte-by-byte and matches its
official Krisdika SHA-256 manifest hash.

Usage:
    python verify_integrity.py --all
    python verify_integrity.py --section 92 --law CRIM_PROC
    python verify_integrity.py --section 334 --law PENAL
    python verify_integrity.py --section 9 --act ACT_TECH_CRIME
"""

import os
import sys
import json
import sqlite3
import hashlib
import argparse

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

LAW_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(LAW_DIR, "raw_sources")
DATA_DIR = os.path.join(LAW_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "thai_law.db")
MANIFEST_PATH = os.path.join(RAW_DIR, "manifest.json")

def compute_sha256(text: str) -> str:
    """Compute SHA-256 hash of UTF-8 normalized text."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def extract_content_from_raw_file(filepath: str) -> str:
    """Read raw source file and strip header comments."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    content_lines = []
    past_header = False
    for line in lines:
        if past_header:
            content_lines.append(line)
        elif not line.startswith("#") and line.strip() == "":
            past_header = True
    return "".join(content_lines).strip()

def verify_single(section_num: str, law_code: str = None, act_slug: str = None, act_name: str = None, verbose: bool = True) -> bool:
    """Verify a single section against raw file, DB, and manifest."""
    if not os.path.exists(MANIFEST_PATH):
        print("[-] manifest.json not found. Run harvester.py first.")
        return False
        
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    sec_meta = None
    manifest_key = None
    
    # Try exact key lookup first
    if act_slug:
        manifest_key = f"{act_slug}_sec_{section_num}"
        sec_meta = manifest.get("sections", {}).get(manifest_key)
    elif law_code:
        manifest_key = f"{law_code}_sec_{section_num}"
        sec_meta = manifest.get("sections", {}).get(manifest_key)
        
    # If not found, scan manifest
    if not sec_meta:
        for k, v in manifest.get("sections", {}).items():
            if str(v.get("section_number")) == str(section_num):
                if act_name and act_name in v.get("act_name", ""):
                    sec_meta = v
                    manifest_key = k
                    break
                elif law_code and v.get("law_code") == law_code:
                    sec_meta = v
                    manifest_key = k
                    break
                elif not law_code and not act_name:
                    sec_meta = v
                    manifest_key = k
                    break

    if not sec_meta:
        target_info = act_slug or law_code or act_name or "ANY"
        print(f"[-] Section {target_info} ม.{section_num} not found in manifest.")
        return False
        
    raw_file_rel = sec_meta["raw_file"]
    raw_file_abs = os.path.join(LAW_DIR, raw_file_rel)
    raw_content = extract_content_from_raw_file(raw_file_abs)
    
    if raw_content is None:
        print(f"[-] Raw file not found: {raw_file_abs}")
        return False
        
    computed_raw_hash = compute_sha256(raw_content)
    manifest_hash = sec_meta["sha256"]
    
    # Query SQLite database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    target_act = sec_meta.get("act_name")
    target_code = sec_meta.get("law_code")
    
    if target_act:
        row = cursor.execute(
            "SELECT content, section_title, act_name, hierarchy_path FROM legal_sections WHERE law_code = ? AND act_name = ? AND section_number = ?",
            (target_code, target_act, section_num)
        ).fetchone()
    else:
        row = cursor.execute(
            "SELECT content, section_title, act_name, hierarchy_path FROM legal_sections WHERE law_code = ? AND section_number = ?",
            (target_code, section_num)
        ).fetchone()
    conn.close()
    
    if not row:
        print(f"[-] Section {target_code} ({target_act}) ม.{section_num} not found in thai_law.db.")
        return False
        
    db_content = row[0].strip()
    db_hash = compute_sha256(db_content)
    
    hash_match = (computed_raw_hash == manifest_hash)
    db_match = (db_content == raw_content)
    is_valid = hash_match and db_match
    
    if verbose:
        sep = "=" * 80
        print(sep)
        print(f"[AUDIT] LEGAL INTEGRITY AUDIT: {row[2]} มาตรา {section_num} ({row[1]})")
        print(sep)
        print(f"  Raw Source File : {raw_file_rel}")
        print(f"  Official URL    : {sec_meta.get('source_url', 'N/A')}")
        print(f"  Manifest Hash   : {manifest_hash}")
        print(f"  Computed Hash   : {computed_raw_hash} [{'MATCH' if hash_match else 'FAIL'}]")
        print(f"  SQLite Match    : [{'100% Byte-by-Byte Match' if db_match else 'MISMATCH'}]")
        print(f"  Length Check    : DB {len(db_content)} chars | Raw {len(raw_content)} chars")
        print(f"  Verdict         : [{'PASS 100% (Krisdika Verbatim Parity)' if is_valid else 'FAIL'}]")
        print(sep)
        print()
        
    return is_valid

def audit_all():
    """Audit every single section in the database against raw sources."""
    if not os.path.exists(MANIFEST_PATH):
        print("[-] manifest.json not found. Run harvester.py first.")
        return False
        
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    sections = manifest.get("sections", {})
    total = len(sections)
    passed = 0
    failed = 0
    
    print(f"[*] Auditing all {total} legal sections in thai_law.db against raw sources...")
    
    for key, meta in sections.items():
        lc = meta["law_code"]
        sn = meta["section_number"]
        an = meta.get("act_name")
        slug = meta.get("act_slug")
        if verify_single(sn, law_code=lc, act_slug=slug, act_name=an, verbose=False):
            passed += 1
        else:
            failed += 1
            print(f"  [X] Failed integrity check: {slug or lc} ม.{sn} ({an})")
            
    print("=" * 60)
    print(f"[SUMMARY] LEGAL INTEGRITY AUDIT:")
    print(f"   Total Sections Audited : {total}")
    print(f"   Passed (100% Verbatim) : {passed}")
    print(f"   Failed (Mismatch)      : {failed}")
    print(f"   Integrity Rate         : {(passed/total)*100:.2f}%")
    print("=" * 60)
    return failed == 0

def main():
    parser = argparse.ArgumentParser(description="Legal Integrity Verification Tool")
    parser.add_argument("--section", help="Section number to verify (e.g. 92, 334)")
    parser.add_argument("--law", default=None, help="Law code: PENAL, CIVIL, CRIM_PROC, CIVIL_PROC, ACT")
    parser.add_argument("--act", default=None, help="Act slug: ACT_TECH_CRIME, ACT_COMP_CRIME, ACT_PDPA, ACT_LABOR, ACT_DEBT_COLLECT, ACT_E_TRANS")
    parser.add_argument("--all", action="store_true", help="Audit all sections in the database")
    
    args = parser.parse_args()
    
    if args.all:
        success = audit_all()
        sys.exit(0 if success else 1)
    elif args.section:
        success = verify_single(args.section, law_code=args.law, act_slug=args.act, verbose=True)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
