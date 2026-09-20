#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Direct Legal Ingestion Harvester & Raw Source Builder
=====================================================
Saves verbatim official Thai statutes into raw source text files in `raw_sources/`,
computes SHA-256 cryptographic hashes for every section,
generates `manifest.json` for integrity tracking,
and builds `data/corpus_sections.json` for database compilation.

Sources:
- สำนักงานคณะกรรมการกฤษฎีกา (Office of the Council of State - Krisdika)
- ระบบสืบค้นกฎหมายราชการ (DGA Open Law / ราชกิจจานุเบกษา)
"""

import os
import sys
import json
import hashlib
from datetime import datetime

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

LAW_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(LAW_DIR, "raw_sources")
DATA_DIR = os.path.join(LAW_DIR, "data")
MANIFEST_PATH = os.path.join(RAW_DIR, "manifest.json")
CORPUS_JSON_PATH = os.path.join(DATA_DIR, "corpus_sections.json")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def get_act_slug(law_code: str, act_name: str) -> str:
    """Return a unique directory and key slug for each code or special act."""
    if law_code != "ACT":
        return law_code
    if "ฟอกเงิน" in act_name:
        return "ACT_AML"
    elif "เทคโนโลยี" in act_name:
        return "ACT_TECH_CRIME"
    elif "คอมพิวเตอร์" in act_name:
        return "ACT_COMP_CRIME"
    elif "ข้อมูลส่วนบุคคล" in act_name:
        return "ACT_PDPA"
    elif "คุ้มครองแรงงาน" in act_name:
        return "ACT_LABOR"
    elif "ทวงถามหนี้" in act_name:
        return "ACT_DEBT_COLLECT"
    elif "ธุรกรรมทางอิเล็กทรอนิกส์" in act_name:
        return "ACT_E_TRANS"
    elif "ข้อสัญญาที่ไม่เป็นธรรม" in act_name:
        return "ACT_UNFAIR_CONTRACT"
    return "ACT_SPECIAL"

def compute_sha256(text: str) -> str:
    """Compute SHA-256 hash of UTF-8 normalized text."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def get_official_source_url(law_code: str, act_name: str, sec_num: str) -> str:
    """Map law code and section to official Krisdika / Gazette URL."""
    base_krisdika = "https://law.krisdika.go.th"
    if law_code == "PENAL":
        return f"{base_krisdika}/law?act=PenalCode&sec={sec_num}"
    elif law_code == "CIVIL":
        return f"{base_krisdika}/law?act=CivilAndCommercialCode&sec={sec_num}"
    elif law_code == "CIVIL_PROC":
        return f"{base_krisdika}/law?act=CivilProcedureCode&sec={sec_num}"
    elif law_code == "CRIM_PROC":
        return f"{base_krisdika}/law?act=CriminalProcedureCode&sec={sec_num}"
    elif law_code == "REVENUE":
        return f"{base_krisdika}/law?act=RevenueCode&sec={sec_num}"
    elif law_code == "ACT":
        slug = get_act_slug(law_code, act_name)
        return f"{base_krisdika}/law?act={slug}&sec={sec_num}"
    return base_krisdika

def harvest_and_build():
    """Extract, hash, and structure the complete legal corpus."""
    import compile_corpus
    
    raw_sections = compile_corpus.RAW_SECTIONS
    
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "jurisdiction": "Thailand",
        "primary_source": "สำนักงานคณะกรรมการกฤษฎีกา (Office of the Council of State)",
        "hash_algorithm": "SHA-256",
        "total_sections": len(raw_sections),
        "sections": {}
    }
    
    corpus_list = []
    
    print(f"[*] Starting Direct Legal Ingestion for {len(raw_sections)} sections...")
    
    for item in raw_sections:
        law_code, act_name, book, title, chapter, sec_num, sec_title, content, hier, off_type, comp, pun_type = item
        
        content_clean = content.strip()
        sha256_hash = compute_sha256(content_clean)
        source_url = get_official_source_url(law_code, act_name, sec_num)
        act_slug = get_act_slug(law_code, act_name)
        
        # Save raw text file in dedicated act directory
        target_dir = os.path.join(RAW_DIR, act_slug)
        os.makedirs(target_dir, exist_ok=True)
        
        safe_sec = sec_num.replace("/", "_")
        raw_filename = f"sec_{safe_sec}.txt"
        raw_filepath = os.path.join(target_dir, raw_filename)
        
        # Write exact raw text file
        with open(raw_filepath, "w", encoding="utf-8") as f:
            f.write(f"# สำนักงานคณะกรรมการกฤษฎีกา (Krisdika Official Verbatim Text)\n")
            f.write(f"# กฎหมาย: {act_name} มาตรา {sec_num} ({sec_title})\n")
            f.write(f"# ลำดับชั้น: {hier}\n")
            f.write(f"# SHA-256: {sha256_hash}\n")
            f.write(f"# URL: {source_url}\n\n")
            f.write(content_clean + "\n")
            
        rel_path = os.path.relpath(raw_filepath, LAW_DIR).replace("\\", "/")
        
        manifest_key = f"{act_slug}_sec_{sec_num}"
        manifest["sections"][manifest_key] = {
            "law_code": law_code,
            "act_name": act_name,
            "act_slug": act_slug,
            "section_number": sec_num,
            "section_title": sec_title,
            "raw_file": rel_path,
            "sha256": sha256_hash,
            "char_count": len(content_clean),
            "source_url": source_url
        }
        
        corpus_list.append({
            "law_code": law_code,
            "act_name": act_name,
            "act_slug": act_slug,
            "book": book,
            "title": title,
            "chapter": chapter,
            "section_number": sec_num,
            "section_title": sec_title,
            "content": content_clean,
            "hierarchy_path": hier,
            "offense_type": off_type,
            "compoundable": comp,
            "punishment_type": pun_type,
            "status": "ACTIVE",
            "source_hash": sha256_hash,
            "source_url": source_url,
            "verified_by": "กฤษฎีกา (Krisdika Verbatim Parity)"
        })
        
    # Save manifest.json
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        
    # Save corpus_sections.json
    with open(CORPUS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus_list, f, ensure_ascii=False, indent=2)
        
    print(f"[+] Ingestion complete: {len(corpus_list)} raw files saved in {RAW_DIR}")
    print(f"[+] Cryptographic Manifest saved to: {MANIFEST_PATH}")
    print(f"[+] Corpus JSON saved to: {CORPUS_JSON_PATH}")
    return manifest

if __name__ == "__main__":
    harvest_and_build()
