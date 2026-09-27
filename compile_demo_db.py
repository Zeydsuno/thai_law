#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compile Sample/Demo Database (thai_law_demo.db)
Extracts a lightweight sandbox corpus (21 core sections, landmark precedents, glossary)
for public evaluation and testing, keeping the full production dataset (142 sections, 1,052 precedents) private.
"""

import os
import sys
import sqlite3

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DB = os.path.join(BASE_DIR, 'data', 'thai_law.db')
DST_DB = os.path.join(BASE_DIR, 'data', 'thai_law_demo.db')

DEMO_SECTIONS = [
    # อาญา - ความผิดต่อชีวิต ร่างกาย ทรัพย์
    '288', '289', '68', '334', '335', '341', '352', '358', '393',
    # แพ่ง - กู้ยืม มรดก ละเมิด ดอกเบี้ย
    '650', '653', '654', '1599', '1629', '1630', '1635', '224', '420',
    # พยานหลักฐาน & ธุรกรรมดิจิทัล
    '94', '7', '8', '9', '11', '12',
    # แรงงาน
    '118', '119'
]

LANDMARK_DIKAS = [
    ('8477', 2563), ('4101', 2562), ('8644', 2561), ('2930', 2551),
    ('1077', 2511), ('256', 2509), ('200', 2511), ('5257', 2548),
    ('4423', 2564), ('352', 2560)
]

def create_demo_db():
    if not os.path.exists(SRC_DB):
        print(f"Source database not found at: {SRC_DB}", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(DST_DB):
        os.remove(DST_DB)

    src = sqlite3.connect(SRC_DB)
    dst = sqlite3.connect(DST_DB)

    cur_src = src.cursor()
    cur_dst = dst.cursor()

    # 1. Create Tables matching compile_corpus.py
    cur_dst.execute('''
    CREATE TABLE legal_sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        law_code TEXT NOT NULL,
        act_name TEXT NOT NULL,
        book TEXT,
        title TEXT,
        chapter TEXT,
        section_number TEXT NOT NULL,
        section_title TEXT,
        content TEXT NOT NULL,
        hierarchy_path TEXT NOT NULL,
        offense_type TEXT,
        compoundable INTEGER DEFAULT 0,
        punishment_type TEXT,
        status TEXT DEFAULT 'ACTIVE',
        effective_date TEXT,
        amended_by TEXT
    )
    ''')

    cur_dst.execute('''
    CREATE VIRTUAL TABLE legal_sections_fts USING fts5(
        section_number, section_title, content, hierarchy_path,
        content='legal_sections', content_rowid='id'
    )
    ''')

    cur_dst.execute('''
    CREATE TABLE cross_references (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_section_id INTEGER NOT NULL,
        to_section_id INTEGER NOT NULL,
        relation_type TEXT NOT NULL,
        is_critical INTEGER DEFAULT 0,
        description TEXT,
        FOREIGN KEY(from_section_id) REFERENCES legal_sections(id),
        FOREIGN KEY(to_section_id) REFERENCES legal_sections(id)
    )
    ''')

    cur_dst.execute('''
    CREATE TABLE legal_precedents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dika_number TEXT NOT NULL,
        year INTEGER,
        is_grand_chamber INTEGER DEFAULT 0,
        case_facts TEXT NOT NULL,
        court_reasoning TEXT NOT NULL,
        related_sections TEXT NOT NULL,
        keywords TEXT
    )
    ''')

    cur_dst.execute('''
    CREATE VIRTUAL TABLE legal_precedents_fts USING fts5(
        dika_number, case_facts, court_reasoning, related_sections, keywords,
        content='legal_precedents', content_rowid='id'
    )
    ''')

    cur_dst.execute('''
    CREATE TABLE legal_glossary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term_th TEXT NOT NULL,
        term_en TEXT,
        definition TEXT NOT NULL,
        source_section TEXT
    )
    ''')

    cur_dst.execute('''
    CREATE VIRTUAL TABLE legal_glossary_fts USING fts5(
        term_th, term_en, definition, source_section,
        content='legal_glossary', content_rowid='id'
    )
    ''')

    # 2. Populate Sections
    placeholders = ','.join('?' for _ in DEMO_SECTIONS)
    cur_src.execute(f'SELECT * FROM legal_sections WHERE section_number IN ({placeholders})', DEMO_SECTIONS)
    sec_rows = cur_src.fetchall()
    if sec_rows:
        cols_q = ','.join('?' for _ in range(len(sec_rows[0])))
        cur_dst.executemany(f'INSERT INTO legal_sections VALUES ({cols_q})', sec_rows)
        cur_dst.execute('''
        INSERT INTO legal_sections_fts(rowid, section_number, section_title, content, hierarchy_path)
        SELECT id, section_number, section_title, content, hierarchy_path FROM legal_sections
        ''')

    # 3. Populate Cross-References (connecting demo sections)
    sec_ids = [r[0] for r in sec_rows]
    id_placeholders = ','.join('?' for _ in sec_ids)
    cur_src.execute(f'SELECT * FROM cross_references WHERE from_section_id IN ({id_placeholders}) AND to_section_id IN ({id_placeholders})', sec_ids + sec_ids)
    ref_rows = cur_src.fetchall()
    if ref_rows:
        ref_cols_q = ','.join('?' for _ in range(len(ref_rows[0])))
        cur_dst.executemany(f'INSERT INTO cross_references VALUES ({ref_cols_q})', ref_rows)

    # 4. Populate Precedents (Landmarks + First 20)
    prec_conditions = []
    prec_params = []
    for d_num, d_yr in LANDMARK_DIKAS:
        prec_conditions.append('(dika_number = ? AND year = ?)')
        prec_params.extend([d_num, d_yr])
    
    where_clause = ' OR '.join(prec_conditions) + ' OR id <= 25'
    cur_src.execute(f'SELECT * FROM legal_precedents WHERE {where_clause}', prec_params)
    prec_rows = cur_src.fetchall()
    if prec_rows:
        prec_cols_q = ','.join('?' for _ in range(len(prec_rows[0])))
        cur_dst.executemany(f'INSERT INTO legal_precedents VALUES ({prec_cols_q})', prec_rows)
        cur_dst.execute('''
        INSERT INTO legal_precedents_fts(rowid, dika_number, case_facts, court_reasoning, related_sections, keywords)
        SELECT id, dika_number, case_facts, court_reasoning, related_sections, keywords FROM legal_precedents
        ''')

    # 5. Populate Glossary (First 20)
    cur_src.execute('SELECT * FROM legal_glossary LIMIT 20')
    glo_rows = cur_src.fetchall()
    if glo_rows:
        glo_cols_q = ','.join('?' for _ in range(len(glo_rows[0])))
        cur_dst.executemany(f'INSERT INTO legal_glossary VALUES ({glo_cols_q})', glo_rows)
        cur_dst.execute('''
        INSERT INTO legal_glossary_fts(rowid, term_th, term_en, definition, source_section)
        SELECT id, term_th, term_en, definition, source_section FROM legal_glossary
        ''')

    dst.commit()
    src.close()
    dst.close()

    size_kb = os.path.getsize(DST_DB) / 1024
    print(f"[+] Successfully compiled Demo Database: {DST_DB}")
    print(f"    - Size: {size_kb:.1f} KB")
    print(f"    - Legal Sections: {len(sec_rows)} core sections")
    print(f"    - Legal Precedents: {len(prec_rows)} landmark precedents")
    print(f"    - Cross References: {len(ref_rows)} links")
    print(f"    - Glossary Terms: {len(glo_rows)} terms")

if __name__ == '__main__':
    create_demo_db()
