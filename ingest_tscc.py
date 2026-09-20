#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TSCC Supreme Court Cases Ingestion Engine
========================================
Downloads and ingests 1,000 authentic Thai Supreme Court criminal precedents (1,207 issues)
from the Thai Supreme Court Cases (TSCC) dataset into `thai_law.db`.

Source:
- Thai Supreme Court Judgement Search System (deka.supremecourt.or.th)
- Curated & verified by KevinMercury/tscc-dataset
"""

import os
import sys
import csv
import io
import re
import urllib.request
import sqlite3

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_PATH = os.path.join(DATA_DIR, 'thai_law.db')
TSCC_CSV_URL = 'https://raw.githubusercontent.com/KevinMercury/tscc-dataset/master/tscc_v0.1-judgement.csv'

CATEGORY_MAP = {
    'LB': 'ความผิดต่อชีวิตและร่างกาย, ฆ่า, ทำร้ายร่างกาย, ประมาท',
    'P': 'ความผิดเกี่ยวกับทรัพย์, ลักทรัพย์, ฉ้อโกง, ยักยอก, วิ่งราว, ชิงทรัพย์, ปล้นทรัพย์',
    'F': 'ความผิดเกี่ยวกับชื่อเสียง, หมิ่นประมาท, ดูหมิ่น'
}

def clean_text(text):
    if not text:
        return ""
    # Remove XML-like tags like <discr>, </discr>
    text = re.sub(r'</?discr>', '', text)
    return text.strip()

def parse_lawids(lawids_str):
    """Convert 'CC-288-00,CC-083-00' -> ['288', '83']"""
    if not lawids_str:
        return []
    matches = re.findall(r'CC-(\d+)-', lawids_str)
    return [str(int(m)) for m in matches]

def ingest_tscc(conn=None):
    close_at_end = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        close_at_end = True

    cursor = conn.cursor()

    # Get valid sections from legal_sections table to ensure integrity
    cursor.execute("SELECT section_number FROM legal_sections")
    valid_sections = set(r[0] for r in cursor.fetchall())

    print(f"[*] Downloading TSCC dataset from {TSCC_CSV_URL}...")
    req = urllib.request.Request(TSCC_CSV_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode('utf-8')

    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    print(f"[*] Parsing {len(rows)} issues from TSCC...")

    # Group issues by dekaid (e.g. '1478/2528') to create comprehensive, clean precedents
    cases_by_deka = {}
    for r in rows:
        deka_full = r['dekaid'].strip()
        if not deka_full or '/' not in deka_full:
            continue
        cases_by_deka.setdefault(deka_full, []).append(r)

    print(f"[*] Found {len(cases_by_deka)} unique Supreme Court judgements.")

    # Check existing dika_number in legal_precedents to avoid duplicates
    cursor.execute("SELECT dika_number, year FROM legal_precedents")
    existing_cases = set((r[0], r[1]) for r in cursor.fetchall())

    inserted = 0
    skipped = 0

    for deka_full, issues in cases_by_deka.items():
        parts = deka_full.split('/')
        dika_no = parts[0].strip()
        try:
            year = int(parts[1].strip())
        except ValueError:
            year = int(issues[0]['year'])

        if (dika_no, year) in existing_cases:
            skipped += 1
            continue

        # Combine case facts (facts are identical or near identical across issues of the same case)
        case_facts = clean_text(issues[0]['fact'])

        # Combine reasoning and decisions across issues
        decisions = []
        all_secs = []
        categories = set()

        for idx, iss in enumerate(issues, 1):
            dec = clean_text(iss['decision'])
            if dec and dec not in decisions:
                if len(issues) > 1:
                    decisions.append(f"[ประเด็นที่ {idx}] {dec}")
                else:
                    decisions.append(dec)
            
            secs = parse_lawids(iss['lawids'])
            for s in secs:
                if s not in all_secs:
                    all_secs.append(s)

            cat = iss.get('category', '')
            if cat in CATEGORY_MAP:
                categories.add(CATEGORY_MAP[cat])

        court_reasoning = "\n".join(decisions)
        
        # Filter related sections that exist in our legal corpus to guarantee referential integrity
        matched_secs = [s for s in all_secs if s in valid_sections]
        related_sections = ", ".join(matched_secs) if matched_secs else "59"

        keywords_list = list(categories)
        keywords = ", ".join(keywords_list) if keywords_list else "คำพิพากษาศาลฎีกา, คดีอาญา"

        cursor.execute('''
            INSERT INTO legal_precedents (dika_number, year, is_grand_chamber, case_facts, court_reasoning, related_sections, keywords)
            VALUES (?, ?, 0, ?, ?, ?, ?)
        ''', (dika_no, year, case_facts, court_reasoning, related_sections, keywords))
        inserted += 1

    conn.commit()
    print(f"[+] Ingestion Complete: {inserted} new Supreme Court precedents inserted ({skipped} already existed).")

    cursor.execute("SELECT COUNT(*) FROM legal_precedents")
    total_precedents = cursor.fetchone()[0]
    print(f"[+] Total Legal Precedents in thai_law.db now: {total_precedents}")

    if close_at_end:
        conn.close()

if __name__ == '__main__':
    ingest_tscc()
