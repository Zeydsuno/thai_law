#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ==============================================================================
# Thai Law RAG Engine - Source-Available (PolyForm Noncommercial License 1.0.0)
# Copyright (c) 2026 Attidmese Bunsua (นายอัตติรมีซี บุญเสือ). All Rights Reserved.
#
# This software, database architecture, and deterministic legal logic are licensed
# under the PolyForm Noncommercial License 1.0.0 for academic research, educational
# purposes, and evaluation only. Commercial exploitation, production hosting, or
# deploying competitive services without prior written agreement is strictly prohibited.
# ==============================================================================
"""
Thai Law RAG Engine (ประมวลกฎหมายอาญา + ประมวลกฎหมายแพ่งและพาณิชย์ + พ.ร.บ.เฉพาะ + 5 Specialized Legal Engines)
Sub-millisecond retrieval with SQLite FTS5, BM25 ranking, Typed Graph Expansion,
Bilingual Colloquial-to-Legal Keyword Mapping, and Automated Legal Calculators & Evidence Engine.
Includes Evidence Admissibility Engine (ป.วิ.พ. ม.94 + พ.ร.บ.ธุรกรรมทางอิเล็กทรอนิกส์).
Designed to address NitiBench failure modes: Context Bloat, Nested Structure, Missable Details, Hidden Hierarchy.
"""

import os
import sys
import json
import sqlite3
import argparse
import zipfile
import datetime

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "data", "thai_law.db")
ZIP_PATH = os.path.join(BASE_DIR, "data", "thai_law.db.zip")

# Auto-extract database if only the compressed zip archive is present
if not os.path.exists(DB_PATH) and os.path.exists(ZIP_PATH):
    try:
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            zf.extractall(os.path.join(BASE_DIR, "data"))
    except Exception as e:
        print(f"Error auto-extracting database: {e}", file=sys.stderr)

THAI_TO_LEGAL_KEYWORDS = {
    # อาญา - ทรัพย์ & ประทุษร้าย
    "ชักดาบ": ["ฉ้อโกง", "341", "หลอกลวง", "ทุจริต"],
    "โดนโกง": ["ฉ้อโกง", "341", "หลอกลวง"],
    "ขโมย": ["ลักทรัพย์", "334", "เอาทรัพย์", "ทุจริต"],
    "ขโมยของ": ["ลักทรัพย์", "334", "เอาทรัพย์"],
    "วิ่งราว": ["วิ่งราวทรัพย์", "336", "ฉกฉวย"],
    "กระชากกระเป๋า": ["วิ่งราวทรัพย์", "336", "ฉกฉวย"],
    "ตบ": ["ทำร้ายร่างกาย", "295", "อันตรายแก่กาย"],
    "ชก": ["ทำร้ายร่างกาย", "295", "อันตรายแก่กาย"],
    "ตี": ["ทำร้ายร่างกาย", "295", "อันตรายแก่กาย"],
    "ทำร้าย": ["ทำร้ายร่างกาย", "295", "อันตรายแก่กาย"],
    "ฆ่า": ["ฆ่าผู้อื่น", "288", "ถึงแก่ความตาย"],
    "ฆ่าคน": ["ฆ่าผู้อื่น", "288", "ประหารชีวิต"],
    "แทง": ["ทำร้ายร่างกาย", "295", "พยายามฆ่า", "288"],
    "ข่มขืน": ["กระทำชำเรา", "276", "ขืนใจ"],
    "หมิ่นประมาท": ["หมิ่นประมาท", "326", "328", "ใส่ความ", "เสียชื่อเสียง"],
    "ด่า": ["ดูหมิ่น", "393", "หมิ่นประมาท", "326"],
    "ยักยอก": ["ยักยอกทรัพย์", "352", "354", "เบียดบัง", "ครอบครอง"],
    "เบียดบัง": ["ยักยอกทรัพย์", "352", "เบียดบัง"],
    "ปล้น": ["ปล้นทรัพย์", "340", "ใช้กำลัง"],
    "ชิงทรัพย์": ["ชิงทรัพย์", "339", "ใช้กำลังประทุษร้าย"],
    "ทำของเสียหาย": ["ทำให้เสียทรัพย์", "358"],
    "เผาบ้าน": ["วางเพลิง", "217", "เผาทรัพย์"],
    "ยาเสพติด": ["ยาเสพติด", "พ.ร.บ.ยาเสพติด"],
    "จ้างวานฆ่า": ["ผู้ใช้", "84", "ฆ่าผู้อื่น", "288"],
    "ยืมรถ": ["ยักยอก", "352", "จำนำ", "รถจักรยานยนต์"],
    "ยืมของ": ["ยักยอก", "352", "ครอบครอง"],
    "ยืม": ["ยักยอก", "ครอบครอง", "352", "กู้ยืม", "653"],
    "จำนำ": ["จำนำ", "ยักยอก", "รับของโจร"],
    "ทำลายหลักฐาน": ["ทำลายพยานหลักฐาน", "177", "ปิดบัง"],
    "แจ้งความเท็จ": ["แจ้งความเท็จ", "137", "เจ้าพนักงาน"],
    "แจ้งเท็จ": ["แจ้งความเท็จ", "137"],
    "ป้องกันเกินสมควร": ["ป้องกันเกินสมควร", "เกินสมควรแก่เหตุ", "69"],
    "ป้องกันตัว": ["ป้องกัน", "68", "ภยันตราย", "ไม่มีความผิด"],
    "อายุความ": ["อายุความ", "95", "96", "ฟ้องคดี"],
    "ยอมความ": ["ยอมความ", "96", "ร้องทุกข์", "3 เดือน"],
    "โกงเจ้าหนี้": ["โกงเจ้าหนี้", "346", "ยักย้ายทรัพย์"],
    "ปลอมเอกสาร": ["ปลอมเอกสาร", "264", "265", "268"],
    "บุกรุก": ["บุกรุก", "362", "เข้าไปในอสังหาริมทรัพย์"],
    "รับของโจร": ["รับของโจร", "357", "ซ่อนเร้น", "รับไว้"],
    "โกงออนไลน์": ["ฉ้อโกง", "341", "343", "อินเทอร์เน็ต", "หลอกขาย"],
    "มือถือหาย": ["ลักทรัพย์", "334", "วิ่งราวทรัพย์", "336"],
    "ขับรถชน": ["ประมาท", "291", "300", "อันตราย"],
    "ขับรถชนคนตาย": ["ประมาท", "291", "ถึงแก่ความตาย"],
    "ทำร้ายร่างกายสาหัส": ["อันตรายสาหัส", "297"],
    "ล่วงละเมิดทางเพศ": ["อนาจาร", "278", "กระทำชำเรา", "276"],
    "เมาแล้วขับ": ["ประมาท", "เมาสุรา", "291"],
    "โพสต์ด่า": ["หมิ่นประมาท", "326", "328", "โฆษณา", "พ.ร.บ.คอม"],
    "คอมเมนต์ด่า": ["หมิ่นประมาท", "326", "328"],
    "ดูหมิ่นศาล": ["ละเมิดอำนาจศาล"],

    # แพ่งและพาณิชย์ - สัญญา หนี้ ละเมิด ครอบครัว มรดก
    "กู้เงิน": ["กู้ยืมเงิน", "653", "654", "ชำระเงิน", "ดอกเบี้ย"],
    "ยืมเงิน": ["กู้ยืมเงิน", "653", "654", "ชำระหนี้"],
    "สัญญากู้": ["กู้ยืมเงิน", "653", "หลักฐานเป็นหนังสือ"],
    "ค้ำประกัน": ["ค้ำประกัน", "680", "681", "686", "ผู้ค้ำ"],
    "เช็คเด้ง": ["เช็ค", "ไม่มีเงิน", "สั่งจ่าย"],
    "ดอกเบี้ย": ["ดอกเบี้ย", "654", "224", "เกินอัตรา", "ผิดนัด"],
    "ดอกโหด": ["ดอกเบี้ยเกินอัตรา", "654", "เงินกู้", "โมฆะ"],
    "ดอกเบี้ยผิดนัด": ["ดอกเบี้ยผิดนัด", "224", "ร้อยละ 5"],
    "ผิดสัญญา": ["ผิดสัญญา", "204", "213", "ชำระหนี้"],
    "ลูกหนี้เบี้ยว": ["ผิดนัด", "204", "213", "บังคับชำระหนี้"],
    "ละเมิด": ["ละเมิด", "420", "425", "438", "ค่าสินไหมทดแทน"],
    "นายจ้างรับผิด": ["ละเมิด", "ทางการที่จ้าง", "425"],
    "ซื้อขาย": ["ซื้อขาย", "456", "สัญญาจะซื้อจะขาย"],
    "เช่าบ้าน": ["เช่าทรัพย์", "538", "เช่าอสังหาริมทรัพย์"],
    "เช่าซื้อ": ["เช่าซื้อ", "572", "รถยนต์"],
    "หย่า": ["หย่า", "1516", "1523", "ฟ้องหย่า", "การสมรส"],
    "ฟ้องหย่า": ["เหตุฟ้องหย่า", "1516", "1523"],
    "ชู้": ["ชู้", "1516", "1523", "ค่าทดแทน", "ชู้สาว"],
    "เมียน้อย": ["ชู้", "1516", "1523", "ค่าทดแทน", "ภริยา"],
    "สินสมรส": ["สินสมรส", "1474", "1471", "แบ่งครึ่ง"],
    "สินส่วนตัว": ["สินส่วนตัว", "1471", "1474"],
    "ของหมั้น": ["หมั้น", "1437", "สินสอด"],
    "สินสอด": ["สินสอด", "1437", "เรียกคืน"],
    "มรดก": ["มรดก", "1599", "1600", "1629", "1630", "1635", "ทายาท"],
    "ทายาท": ["ทายาทโดยธรรม", "1629", "1630", "1635", "ผู้สืบสันดาน"],
    "ทายาทโดยธรรม": ["ทายาทโดยธรรม", "1629", "1635", "ผู้สืบสันดาน"],
    "ส่วนแบ่งมรดก": ["มรดก", "1629", "1635", "คู่สมรส"],
    "บุตรนอกกฎหมาย": ["บุตรนอกสมรส", "1627", "บิดารับรอง", "มรดก"],
    "ผู้จัดการมรดก": ["ผู้จัดการมรดก", "1600", "354", "ยักยอกมรดก"],
    "โมฆะ": ["โมฆะ", "150", "155", "156", "เสียเปล่า"],
    "โมฆียะ": ["โมฆียะ", "157", "159", "164", "175", "บอกล้าง"],

    # พ.ร.บ. เฉพาะ (เทคโนโลยี แรงงาน ทวงหนี้ PDPA)
    "บัญชีม้า": ["บัญชีม้า", "9", "10", "พ.ร.ก. เทคโนโลยีฯ", "ฉ้อโกงประชาชน"],
    "ซิมม้า": ["ซิมม้า", "9", "10", "พ.ร.ก. เทคโนโลยีฯ"],
    "รับจ้างเปิดบัญชี": ["บัญชีม้า", "9", "พ.ร.ก. เทคโนโลยีฯ"],
    "พ.ร.บ.คอม": ["พ.ร.บ. คอมพิวเตอร์", "14", "16", "ข้อมูลเท็จ", "นำเข้าสู่ระบบ"],
    "พรบคอม": ["พ.ร.บ. คอมพิวเตอร์", "14", "16"],
    "ตัดต่อรูป": ["16", "พ.ร.บ. คอมพิวเตอร์", "ภาพตัดต่อ", "อับอาย"],
    "รูปโป๊": ["14", "พ.ร.บ. คอมพิวเตอร์", "ลามก"],
    "ทวงหนี้": ["ทวงถามหนี้", "11", "ประจาน", "ข่มขู่"],
    "ประจาน": ["ทวงถามหนี้", "11", "328", "หมิ่นประมาทโดยการโฆษณา"],
    "โพสต์ประจาน": ["11", "328", "พ.ร.บ. ทวงถามหนี้", "หมิ่นประมาท"],
    "เลิกจ้าง": ["เลิกจ้าง", "118", "119", "ค่าชดเชย", "พ.ร.บ. คุ้มครองแรงงาน"],
    "ค่าชดเชย": ["ค่าชดเชย", "118", "119", "เลิกจ้าง"],
    "ค่าตกใจ": ["ค่าตกใจ", "118", "บอกกล่าวล่วงหน้า", "สินจ้าง"],
    "ไล่ออก": ["เลิกจ้าง", "118", "119", "ค่าชดเชย"],
    "PDPA": ["ข้อมูลส่วนบุคคล", "24", "27", "77", "ยินยอม"],
    "ข้อมูลส่วนบุคคล": ["PDPA", "24", "27", "77", "ยินยอม", "ค่าสินไหมทดแทน"],
    "แอบปล่อยข้อมูล": ["PDPA", "27", "77", "เปิดเผย"],

    # กฎหมายลักษณะพยาน & พยานหลักฐานดิจิทัล
    "หลักฐาน": ["พยานหลักฐาน", "226", "226/1", "84", "11"],
    "พยาน": ["พยานหลักฐาน", "226", "226/1", "84", "94", "95/1"],
    "แอบอัดเสียง": ["226", "226/1", "บันทึกเสียง", "พยานหลักฐานที่ได้มาโดยมิชอบ"],
    "อัดเสียง": ["226", "226/1", "บันทึกเสียง"],
    "ดักฟัง": ["226/1", "พยานหลักฐานที่ได้มาโดยมิชอบ"],
    "แคปจอ": ["พ.ร.บ. ธุรกรรม", "11", "8", "ข้อมูลอิเล็กทรอนิกส์"],
    "แคปแชต": ["พ.ร.บ. ธุรกรรม", "11", "8", "ข้อมูลอิเล็กทรอนิกส์", "653"],
    "ภาพแคป": ["11", "8", "พ.ร.บ. ธุรกรรม", "ข้อมูลอิเล็กทรอนิกส์"],
    "พยานบอกเล่า": ["พยานบอกเล่า", "95/1", "226/3"],
    "ภาระการพิสูจน์": ["ภาระการพิสูจน์", "84", "หน้าที่นำสืบ"],
    "สงสัย": ["ยกประโยชน์แห่งความสงสัย", "227"],
    "ได้มาโดยมิชอบ": ["226/1", "พยานหลักฐานที่ได้มาโดยมิชอบ"],
    "พยานบุคคล": ["พยานบุคคล", "94", "สืบพยานบุคคล"],

    # ป.วิ.อ. - การค้นในที่รโหฐาน & หมายค้น
    "ค้นบ้าน": ["การค้นในที่รโหฐาน", "92", "96", "102", "หมายค้น", "ที่รโหฐาน"],
    "ค้น": ["การค้นในที่รโหฐาน", "92", "96", "102", "หมายค้น", "ที่รโหฐาน"],
    "ตรวจค้น": ["การค้นในที่รโหฐาน", "92", "96", "102", "หมายค้น", "ที่รโหฐาน"],
    "หมายค้น": ["การค้นในที่รโหฐาน", "92", "96", "102", "หมายค้น", "ที่รโหฐาน"],
    "ที่รโหฐาน": ["การค้นในที่รโหฐาน", "92", "96", "102", "เคหสถาน", "ที่รโหฐาน"],
    "ตำรวจค้นบ้าน": ["92", "96", "102", "การค้นในที่รโหฐาน", "หมายค้น"],
    "ค้นกลางคืน": ["96", "4950", "การค้นในที่รโหฐาน", "เวลากลางคืน"],
    "ค้นโดยไม่มีหมาย": ["92", "1164", "3578", "ข้อยกเว้น", "การค้นในที่รโหฐาน"],
    "ค้นมิชอบ": ["92", "96", "226", "226/1", "1493", "1164", "3578"],
    "ไม่มีหมายค้น": ["92", "1493", "1164", "3578", "พยานหลักฐานที่ได้มาโดยมิชอบ"],

    # เว็บพนันออนไลน์, การอยู่ร่วมบ้าน, และการฟอกเงิน
    "เว็บพนัน": ["5", "83", "86", "ฟอกเงิน", "4423", "7290", "8345", "การพนัน"],
    "พนันออนไลน์": ["5", "83", "86", "ฟอกเงิน", "7290", "การพนัน"],
    "ฟอกเงิน": ["5", "ฟอกเงิน", "7290", "8345", "ความผิดมูลฐาน"],
    "อยู่บ้านเดียวกัน": ["83", "86", "4423", "ตัวการ", "ผู้สนับสนุน"],
    "คนในบ้าน": ["83", "86", "4423", "ครอบครัว", "ร่วมกัน", "ตัวการร่วม"],
    "เงินใช้จ่ายในบ้าน": ["5", "59", "4423", "7290", "8345", "ฟอกเงิน", "ขาดเจตนา"],

    # ตัวการไม่เปิดเผยชื่อ, การกู้ร่วม, ถือกรรมสิทธิ์แทน, ยืมชื่อกู้
    "ยืมชื่อ": ["806", "155", "702", "ตัวการไม่เปิดเผยชื่อ", "ถือกรรมสิทธิ์แทน", "8477"],
    "ยืมชื่อกู้": ["806", "155", "702", "653", "ตัวการไม่เปิดเผยชื่อ", "ถือกรรมสิทธิ์แทน", "8477", "นิติกรรมอำพราง"],
    "กู้แทน": ["806", "155", "702", "653", "ตัวการไม่เปิดเผยชื่อ", "ถือกรรมสิทธิ์แทน", "8477"],
    "กู้ซื้อบ้าน": ["806", "702", "653", "จำนอง", "ถือกรรมสิทธิ์แทน", "8477"],
    "ถือกรรมสิทธิ์แทน": ["806", "702", "155", "ตัวการไม่เปิดเผยชื่อ", "8477", "4870"],
    "ตัวการไม่เปิดเผยชื่อ": ["806", "702", "155", "ตัวแทน", "8477", "4870"],
    "เพื่อนไม่ผ่อน": ["806", "702", "653", "341", "8477", "973", "ผิดสัญญาแพ่ง"],
    "ฟ้องขับไล่": ["1336", "420", "ขับไล่", "กรรมสิทธิ์"],

    # ข้อสัญญาที่ไม่เป็นธรรม & เบี้ยปรับ & มัดจำ
    "ข้อสัญญาไม่เป็นธรรม": ["ข้อสัญญาที่ไม่เป็นธรรม", "สัญญาสำเร็จรูป", "พ.ร.บ.ว่าด้วยข้อสัญญาที่ไม่เป็นธรรม"],
    "สัญญาไม่เป็นธรรม": ["ข้อสัญญาที่ไม่เป็นธรรม", "สัญญาสำเร็จรูป", "พ.ร.บ.ว่าด้วยข้อสัญญาที่ไม่เป็นธรรม"],
    "สัญญาสำเร็จรูป": ["สัญญาสำเร็จรูป", "ข้อสัญญาที่ไม่เป็นธรรม"],
    "เบี้ยปรับสูงเกินส่วน": ["เบี้ยปรับ", "383", "ข้อสัญญาที่ไม่เป็นธรรม"],
    "ริบมัดจำ": ["มัดจำ", "378", "ริบมัดจำ", "ข้อสัญญาที่ไม่เป็นธรรม"],
    "ยกเว้นความรับผิด": ["ข้อตกลงยกเว้นความรับผิด", "ข้อสัญญาที่ไม่เป็นธรรม", "โมฆะ"],
    "มัดจำ": ["มัดจำ", "378", "วางประจำ", "456"],
    "เบี้ยปรับ": ["เบี้ยปรับ", "383", "ลดเบี้ยปรับ"],
    "ตีความสัญญาสำเร็จรูป": ["สัญญาสำเร็จรูป", "การตีความ", "เป็นคุณ", "ข้อสัญญาที่ไม่เป็นธรรม"],
    "เลิกสัญญาไม่เป็นธรรม": ["ข้อตกลงให้สิทธิเลิกสัญญา", "เลิกสัญญา", "ข้อสัญญาที่ไม่เป็นธรรม"],

    # ประมวลรัษฎากร & ภาษีอากร
    "ภาษี": ["ประมวลรัษฎากร", "เงินได้พึงประเมิน", "40", "ภาษีเงินได้"],
    "ภาษีเงินได้": ["เงินได้พึงประเมิน", "40", "หัก ณ ที่จ่าย", "50", "ประมวลรัษฎากร"],
    "ภาษีบุคคลธรรมดา": ["เงินได้พึงประเมิน", "39", "40", "50"],
    "ภาษีนิติบุคคล": ["กำไรสุทธิ", "65", "65 ตรี", "67 ทวิ", "ประมวลรัษฎากร"],
    "หัก ณ ที่จ่าย": ["หักภาษี ณ ที่จ่าย", "50", "19", "ประมวลรัษฎากร"],
    "เงินเพิ่ม": ["เงินเพิ่ม", "89/1", "ร้อยละ 1.5", "เบี้ยปรับภาษี", "89"],
    "เบี้ยปรับภาษี": ["เบี้ยปรับ", "89", "เงินเพิ่ม", "89/1", "ประมวลรัษฎากร"],
    "รายจ่ายต้องห้าม": ["รายจ่ายต้องห้าม", "65 ตรี", "กำไรสุทธิ", "ภาษีนิติบุคคล"],
    "หมายเรียกภาษี": ["หมายเรียก", "19", "เจ้าพนักงานประเมิน", "ประมวลรัษฎากร"],
    "ตรวจสอบภาษี": ["หมายเรียก", "19", "ประมวลรัษฎากร", "เจ้าพนักงานประเมิน"],

    # พยานหลักฐาน & Parol Evidence Rule & ธุรกรรมทางอิเล็กทรอนิกส์
    "แชทไลน์เป็นหลักฐาน": ["8", "9", "11", "12", "พ.ร.บ. ธุรกรรม", "653", "ลายมือชื่ออิเล็กทรอนิกส์"],
    "สลิปโอนเงิน": ["650", "การส่งมอบทรัพย์สิน", "11", "12", "พ.ร.บ. ธุรกรรม"],
    "ห้ามสืบพยานบุคคล": ["94", "สืบพยานบุคคล", "พยานเอกสาร", "ข้อยกเว้น"],
    "นิติกรรมอำพราง": ["155", "94", "สืบหักล้าง", "4101"],
    "ไม่มีการส่งมอบเงิน": ["650", "94", "สืบหักล้าง", "4101", "8477"]
}

def expand_query(query):
    expanded = set()
    if query:
        expanded.add(query)
    for part in query.split():
        if len(part) > 1:
            expanded.add(part)
    for k, v in THAI_TO_LEGAL_KEYWORDS.items():
        if k in query:
            if k == "ตี" and ("ตีความ" in query or "ตีราคา" in query):
                continue
            expanded.update(v)
    return " OR ".join(f'"{t}"' for t in expanded if t)

_DB_CONN = None

def get_db_connection():
    global _DB_CONN
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run compile_corpus.py first.")
    if _DB_CONN is not None:
        try:
            _DB_CONN.execute("SELECT 1")
            return _DB_CONN
        except Exception:
            _DB_CONN = None
            
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Ponytail Must-Have High-Performance PRAGMAs (<1ms query latency)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -16000;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA mmap_size = 268435456;")
    _DB_CONN = conn
    return conn

def search_sections(query, limit=5, law_code=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    expanded_query = expand_query(query)
    results = []
    
    # Try FTS5 first
    try:
        sql = """
            SELECT ls.id, ls.law_code, ls.section_number, ls.section_title as title, ls.content,
                   ls.hierarchy_path, ls.compoundable, ls.punishment_type as penalty_text, ls.status
            FROM legal_sections_fts fts
            JOIN legal_sections ls ON fts.rowid = ls.id
            WHERE legal_sections_fts MATCH ? AND ls.status = 'ACTIVE'
        """
        params = [expanded_query]
        if law_code:
            sql += " AND ls.law_code = ?"
            params.append(law_code)
            
        sql += " ORDER BY fts.rank LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
    except Exception:
        results = []
    
    # Supplemental / Fallback search via LIKE if FTS returns fewer than limit
    if len(results) < limit:
        seen_ids = set(r['id'] for r in results)
        like_terms = [query]
        for part in query.split():
            if len(part) > 1:
                like_terms.append(part)
        for k, v in THAI_TO_LEGAL_KEYWORDS.items():
            if k in query:
                like_terms.extend(v)
                
        for t in sorted(set(like_terms), key=len, reverse=True):
            if not t or len(t) < 2:
                continue
            sql = """
                SELECT id, law_code, section_number, section_title as title, content,
                       hierarchy_path, compoundable, punishment_type as penalty_text, status
                FROM legal_sections
                WHERE (section_title LIKE ? OR content LIKE ? OR section_number = ?) AND status = 'ACTIVE'
            """
            like_query = f"%{t}%"
            params = [like_query, like_query, t]
            if law_code:
                sql += " AND law_code = ?"
                params.append(law_code)
            sql += " LIMIT ?"
            params.append(limit - len(results))
            cursor.execute(sql, params)
            for r in cursor.fetchall():
                if r['id'] not in seen_ids:
                    seen_ids.add(r['id'])
                    results.append(r)
            if len(results) >= limit:
                break
        
    return [dict(r) for r in results[:limit]]

def get_section(section_number, law_code='PENAL'):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, law_code, section_number, section_title as title, content,
               hierarchy_path, compoundable, punishment_type as penalty_text, status
        FROM legal_sections
        WHERE section_number = ? AND (law_code = ? OR ? IS NULL) AND status = 'ACTIVE'
        LIMIT 1
    """, (section_number, law_code, law_code))
    
    row = cursor.fetchone()
    if not row:
        return None
        
    result = dict(row)
    result['critical_refs'] = []
    
    # Fetch critical cross-references
    cursor.execute("""
        SELECT cr.relation_type as relationship_type, ls.section_number, ls.section_title as title,
               ls.content, ls.law_code
        FROM cross_references cr
        JOIN legal_sections ls ON cr.to_section_id = ls.id
        WHERE cr.from_section_id = ? AND cr.is_critical = 1 AND ls.status = 'ACTIVE'
    """, (result['id'],))
    
    refs = cursor.fetchall()
    for ref in refs:
        result['critical_refs'].append(dict(ref))
        
    return result

def get_cross_refs(section_number, law_code='PENAL'):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM legal_sections 
        WHERE section_number = ? AND (law_code = ? OR ? IS NULL) AND status = 'ACTIVE'
        LIMIT 1
    """, (section_number, law_code, law_code))
    
    row = cursor.fetchone()
    if not row:
        return []
        
    cursor.execute("""
        SELECT cr.relation_type as relationship_type, cr.is_critical, ls.section_number,
               ls.section_title as title, ls.law_code, cr.description
        FROM cross_references cr
        JOIN legal_sections ls ON cr.to_section_id = ls.id
        WHERE cr.from_section_id = ? AND ls.status = 'ACTIVE'
    """, (row['id'],))
    
    refs = cursor.fetchall()
    return [dict(r) for r in refs]

def search_precedents(query, limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    expanded_query = expand_query(query)
    results = []
    
    # Try FTS5 first
    try:
        sql = """
            SELECT lp.id, lp.dika_number, lp.year, lp.is_grand_chamber,
                   lp.case_facts as summary, lp.court_reasoning as details, lp.related_sections
            FROM legal_precedents_fts fts
            JOIN legal_precedents lp ON fts.rowid = lp.id
            WHERE legal_precedents_fts MATCH ?
            ORDER BY fts.rank LIMIT ?
        """
        cursor.execute(sql, (expanded_query, limit))
        results = cursor.fetchall()
    except Exception:
        results = []
    
    # Fallback to LIKE
    if not results:
        like_terms = [query]
        for k, v in THAI_TO_LEGAL_KEYWORDS.items():
            if k in query:
                like_terms.extend(v)
        if " " in query:
            like_terms.extend(query.split())
            
        seen_ids = set()
        for t in like_terms:
            sql = """
                SELECT id, dika_number, year, is_grand_chamber,
                       case_facts as summary, court_reasoning as details, related_sections
                FROM legal_precedents
                WHERE case_facts LIKE ? OR court_reasoning LIKE ? OR related_sections LIKE ? OR dika_number LIKE ? OR keywords LIKE ?
                LIMIT ?
            """
            like_query = f"%{t}%"
            cursor.execute(sql, (like_query, like_query, like_query, like_query, like_query, limit - len(results)))
            for r in cursor.fetchall():
                if r['id'] not in seen_ids:
                    seen_ids.add(r['id'])
                    results.append(r)
            if len(results) >= limit:
                break
        
    return [dict(r) for r in results]

def get_precedent(dika_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    dika_str = str(dika_number).strip()
    if "/" in dika_str:
        parts = dika_str.split("/")
        num_part = parts[0].strip()
        year_part = parts[1].strip()
        cursor.execute("""
            SELECT id, dika_number, year, is_grand_chamber,
                   case_facts as summary, court_reasoning as details, related_sections
            FROM legal_precedents
            WHERE dika_number LIKE ? AND (year = ? OR year LIKE ?)
            LIMIT 1
        """, (f"%{num_part}%", year_part, f"%{year_part}%"))
    else:
        cursor.execute("""
            SELECT id, dika_number, year, is_grand_chamber,
                   case_facts as summary, court_reasoning as details, related_sections
            FROM legal_precedents
            WHERE dika_number LIKE ?
            LIMIT 1
        """, (f"%{dika_number}%",))
    
    row = cursor.fetchone()
    return dict(row) if row else None

def fetch_official_dika(dika_number, year=None, force_refresh=False):
    """
    Fetch authentic, official Supreme Court judgement directly from deka.supremecourt.or.th
    via deterministic POST lookup with Tier 3 Auto-Ingestion and Smart Local Caching.
    Zero hallucination, 100% verbatim from Court of Justice.
    """
    dika_str = str(dika_number).strip()
    if "/" in dika_str and not year:
        parts = dika_str.split("/")
        dika_no = parts[0].strip()
        year = parts[1].strip()
    else:
        dika_no = dika_str
        year = str(year).strip() if year else ""
        
    if not year:
        raise ValueError("ต้องระบุทั้งเลขฎีกาและปี พ.ศ. เช่น fetch_official_dika(8477, 2563) หรือ '8477/2563'")

    # 1. Tier 3 Cache Lookup: Check local SQLite DB first (<1ms latency)
    if not force_refresh:
        local_rec = get_precedent(f"{dika_no}/{year}")
        if local_rec and (local_rec.get("summary") or local_rec.get("details")):
            gc_str = " (ที่ประชุมใหญ่)" if local_rec.get('is_grand_chamber') else ""
            return {
                "success": True,
                "dika_number": f"{dika_no}/{year}",
                "title": f"คำพิพากษาศาลฎีกาที่ {dika_no}/{year}{gc_str}",
                "summary": local_rec.get("summary", ""),
                "full_text": local_rec.get("details", ""),
                "source_url": "https://deka.supremecourt.or.th (Local SQLite Cache)",
                "verified_by": "สำนักงานศาลยุติธรรม (Court of Justice Official Portal - Cached)",
                "from_cache": True
            }

    import urllib.request
    import urllib.parse
    import re
    import html as html_module

    url = "https://deka.supremecourt.or.th/search"
    payload = {
        'search_form_type': 'basic',
        'start': 'true',
        'search_doctype': '1',
        'search_type': '1',
        'search_deka_no': str(dika_no),
        'search_deka_start_year': str(year),
        'search_deka_end_year': str(year)
    }
    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw_html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return {
            "success": False,
            "error": f"ไม่สามารถเชื่อมต่อศาลฎีกา (deka.supremecourt.or.th): {str(e)}",
            "dika_number": f"{dika_no}/{year}",
            "from_cache": False
        }

    # Extract title
    title_match = re.search(r'class="[^"]*content-title[^"]*">\s*([^<]+)', raw_html)
    title = title_match.group(1).strip() if title_match else f"ฎีกาที่ {dika_no}/{year}"

    # Extract short summary (ย่อสั้น)
    short_match = re.search(r'id=["\']short_text_docid_\d+["\'][^>]*>(.*?)</li>', raw_html, re.DOTALL)
    short_text = ""
    if short_match:
        clean = re.sub(r'<[^>]+>', '\n', short_match.group(1))
        clean = html_module.unescape(clean)
        short_text = "\n".join([line.strip() for line in clean.splitlines() if line.strip()])

    # Extract long text (ย่อยาว / คำวินิจฉัยเต็ม)
    long_match = re.search(r'id=["\']long_text_docid_\d+["\'][^>]*>(.*?)</li>', raw_html, re.DOTALL)
    long_text = ""
    if long_match:
        clean = re.sub(r'<[^>]+>', '\n', long_match.group(1))
        clean = html_module.unescape(clean)
        long_text = "\n".join([line.strip() for line in clean.splitlines() if line.strip()])

    found = bool(short_text or long_text)

    # 2. Tier 3 Auto-Ingestion: Persist fetched dika into local SQLite DB
    if found:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            is_gc = 1 if ("ที่ประชุมใหญ่" in title or "(ป)" in title or "(ป.)" in title) else 0
            yr = int(year) if str(year).isdigit() else None
            clean_dika = str(dika_no).strip()

            cursor.execute("""
                SELECT id FROM legal_precedents 
                WHERE (dika_number = ? OR dika_number = ?) AND (year = ? OR year IS NULL)
            """, (clean_dika, f"{clean_dika}/{year}", yr))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE legal_precedents
                    SET case_facts = ?, court_reasoning = ?, is_grand_chamber = ?
                    WHERE id = ?
                """, (short_text, long_text if long_text else short_text, is_gc, row['id']))
            else:
                cursor.execute("""
                    INSERT INTO legal_precedents 
                    (dika_number, year, is_grand_chamber, case_facts, court_reasoning, related_sections, keywords)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (clean_dika, yr, is_gc, short_text, long_text if long_text else short_text, "", title))
            conn.commit()
            conn.close()
        except Exception:
            pass

    return {
        "success": found,
        "dika_number": f"{dika_no}/{year}",
        "title": title,
        "summary": short_text if short_text else ("ไม่พบเนื้อหาย่อสั้น" if not found else "ไม่มีข้อมูลย่อสั้นจากระบบศาล"),
        "full_text": long_text if long_text else "",
        "source_url": "https://deka.supremecourt.or.th",
        "verified_by": "สำนักงานศาลยุติธรรม (Court of Justice Official Portal)",
        "from_cache": False
    }

def search_glossary(query, limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    results = []
    
    expanded_query = expand_query(query)
    
    # Try FTS5 first
    try:
        sql = """
            SELECT lg.id, lg.term_th as term, lg.term_en, lg.definition, lg.source_section as reference
            FROM legal_glossary_fts fts
            JOIN legal_glossary lg ON fts.rowid = lg.id
            WHERE legal_glossary_fts MATCH ?
            ORDER BY fts.rank LIMIT ?
        """
        cursor.execute(sql, (expanded_query, limit))
        results = cursor.fetchall()
    except Exception:
        results = []
    
    # Fallback to LIKE
    if not results:
        like_terms = [query]
        for k, v in THAI_TO_LEGAL_KEYWORDS.items():
            if k in query:
                like_terms.extend(v)
                
        seen_ids = set()
        for t in like_terms:
            sql = """
                SELECT id, term_th as term, term_en, definition, source_section as reference
                FROM legal_glossary
                WHERE term_th LIKE ? OR definition LIKE ?
                LIMIT ?
            """
            like_query = f"%{t}%"
            cursor.execute(sql, (like_query, like_query, limit - len(results)))
            for r in cursor.fetchall():
                if r['id'] not in seen_ids:
                    seen_ids.add(r['id'])
                    results.append(r)
            if len(results) >= limit:
                break
                
    return [dict(r) for r in results]

def get_glossary_term(term):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, term_th as term, term_en, definition, source_section as reference
        FROM legal_glossary
        WHERE term_th LIKE ? OR term_en LIKE ?
        LIMIT 1
    """, (f"%{term}%", f"%{term}%"))
    
    row = cursor.fetchone()
    return dict(row) if row else None


# ==============================================================================
# 4 LEGAL CALCULATORS (คำนวณมรดก อายุความ ค่าชดเชยแรงงาน ดอกเบี้ยผิดนัด)
# ==============================================================================

def calculate_thai_inheritance(estate_value, has_spouse=False, num_children=0, num_parents=0,
                               num_full_siblings=0, num_half_siblings=0, num_grandparents=0,
                               num_uncles_aunts=0):
    """
    คำนวณสัดส่วนการแบ่งทรัพย์มรดกตามประมวลกฎหมายแพ่งและพาณิชย์ (ป.พ.พ. ม.1599, 1629, 1630, 1635)
    หลักเกณฑ์:
      - ลำดับ 1 (ผู้สืบสันดาน) และ ลำดับ 2 (บิดามารดา): ม.1630 วรรคสอง บิดามารดารับส่วนแบ่งเสมือนชั้นบุตร
      - คู่สมรส (ม.1635):
        (1) ร่วมกับบุตร/บิดามารดา: ได้รับเสมือนทายาทชั้นบุตร (หารเท่า)
        (2) ร่วมกับพี่น้องร่วมบิดามารดา หรือ บิดามารดา (กรณีไม่มีบุตร): ได้ 1/2
        (3) ร่วมกับลำดับ 4, 5, 6: ได้ 2/3
        (4) ไม่มีทายาทอื่นเลย: ได้ทั้งหมด 100%
      - ญาติสนิทตัดญาติห่าง (ม.1630 วรรคแรก)
    """
    estate = float(estate_value)
    if estate <= 0:
        return {
            "estate_value": 0.0,
            "shares": {},
            "citations": ["ป.พ.พ. มาตรา 1599, 1600"],
            "explanation": "กองมรดกไม่มีทรัพย์สินหรือมีมูลค่าไม่เกิน 0 บาท"
        }

    shares = {}
    citations = ["ป.พ.พ. มาตรา 1599", "ป.พ.พ. มาตรา 1629"]
    explanation_parts = []

    # ตรวจสอบว่ามีทายาทลำดับ 1 หรือ 2 หรือไม่
    if num_children > 0 or num_parents > 0:
        citations.append("ป.พ.พ. มาตรา 1630 (ญาติสนิทตัดญาติห่าง ยกเว้นบิดามารดา)")
        if num_children > 0:
            # กรณีมีบุตร
            if has_spouse:
                citations.append("ป.พ.พ. มาตรา 1635(1) (คู่สมรสได้ส่วนแบ่งเสมือนทายาทชั้นบุตร)")
                total_heads = num_children + num_parents + 1
                each_share = estate / total_heads
                shares["คู่สมรส"] = {"amount": each_share, "percent": round(100.0 / total_heads, 2), "heads": 1}
                shares["บุตร (ผู้สืบสันดาน)"] = {"amount": each_share * num_children, "per_head": each_share, "percent": round((100.0 * num_children) / total_heads, 2), "heads": num_children}
                if num_parents > 0:
                    shares["บิดามารดา"] = {"amount": each_share * num_parents, "per_head": each_share, "percent": round((100.0 * num_parents) / total_heads, 2), "heads": num_parents}
                explanation_parts.append(f"มีบุตรและคู่สมรส แบ่งเท่ากันคนละ 1 ส่วน (รวม {total_heads} ส่วน)")
            else:
                total_heads = num_children + num_parents
                each_share = estate / total_heads
                shares["บุตร (ผู้สืบสันดาน)"] = {"amount": each_share * num_children, "per_head": each_share, "percent": round((100.0 * num_children) / total_heads, 2), "heads": num_children}
                if num_parents > 0:
                    shares["บิดามารดา"] = {"amount": each_share * num_parents, "per_head": each_share, "percent": round((100.0 * num_parents) / total_heads, 2), "heads": num_parents}
                explanation_parts.append(f"มีบุตร (และบิดามารดา) ไม่มีคู่สมรส แบ่งเท่ากันคนละ 1 ส่วน (รวม {total_heads} ส่วน)")
        else:
            # ไม่มีบุตร แต่มีบิดามารดา
            if has_spouse:
                citations.append("ป.พ.พ. มาตรา 1635(2) (คู่สมรสได้รับกึ่งหนึ่ง)")
                spouse_share = estate * 0.5
                parents_share = estate * 0.5
                shares["คู่สมรส"] = {"amount": spouse_share, "percent": 50.0, "heads": 1}
                shares["บิดามารดา"] = {"amount": parents_share, "per_head": parents_share / num_parents, "percent": 50.0, "heads": num_parents}
                explanation_parts.append("ไม่มีบุตร มีบิดามารดาและคู่สมรส: คู่สมรสได้รับกึ่งหนึ่ง (50%) บิดามารดาแบ่งกึ่งหนึ่งที่เหลือ (50%)")
            else:
                each_share = estate / num_parents
                shares["บิดามารดา"] = {"amount": estate, "per_head": each_share, "percent": 100.0, "heads": num_parents}
                explanation_parts.append(f"ไม่มีบุตรและคู่สมรส บิดามารดารับมรดกทั้งหมด แบ่งเท่ากัน {num_parents} คน")

    # ลำดับ 3: พี่น้องร่วมบิดามารดาเดียวกัน
    elif num_full_siblings > 0:
        citations.append("ป.พ.พ. มาตรา 1629(3)")
        if has_spouse:
            citations.append("ป.พ.พ. มาตรา 1635(2) (คู่สมรสได้รับกึ่งหนึ่ง)")
            spouse_share = estate * 0.5
            sibling_share = estate * 0.5
            shares["คู่สมรส"] = {"amount": spouse_share, "percent": 50.0, "heads": 1}
            shares["พี่น้องร่วมบิดามารดา"] = {"amount": sibling_share, "per_head": sibling_share / num_full_siblings, "percent": 50.0, "heads": num_full_siblings}
            explanation_parts.append("ไม่มีลำดับ 1-2: คู่สมรสได้รับกึ่งหนึ่ง (50%) พี่น้องร่วมบิดามารดาแบ่งกึ่งหนึ่งที่เหลือ (50%)")
        else:
            each_share = estate / num_full_siblings
            shares["พี่น้องร่วมบิดามารดา"] = {"amount": estate, "per_head": each_share, "percent": 100.0, "heads": num_full_siblings}
            explanation_parts.append(f"ไม่มีทายาทลำดับ 1-2 และไม่มีคู่สมรส: พี่น้องร่วมบิดามารดารับมรดกทั้งหมด แบ่ง {num_full_siblings} คน")

    # ลำดับ 4: พี่น้องร่วมบิดาหรือร่วมมารดาเดียวกัน
    elif num_half_siblings > 0:
        citations.append("ป.พ.พ. มาตรา 1629(4)")
        if has_spouse:
            citations.append("ป.พ.พ. มาตรา 1635(3) (คู่สมรสได้รับสองในสามส่วน)")
            spouse_share = estate * (2.0 / 3.0)
            sibling_share = estate * (1.0 / 3.0)
            shares["คู่สมรส"] = {"amount": spouse_share, "percent": 66.67, "heads": 1}
            shares["พี่น้องร่วมบิดาหรือมารดา"] = {"amount": sibling_share, "per_head": sibling_share / num_half_siblings, "percent": 33.33, "heads": num_half_siblings}
            explanation_parts.append("ไม่มีลำดับ 1-3: คู่สมรสได้รับ 2/3 (66.67%) พี่น้องร่วมบิดาหรือมารดาแบ่ง 1/3 ที่เหลือ (33.33%)")
        else:
            each_share = estate / num_half_siblings
            shares["พี่น้องร่วมบิดาหรือมารดา"] = {"amount": estate, "per_head": each_share, "percent": 100.0, "heads": num_half_siblings}
            explanation_parts.append(f"พี่น้องร่วมบิดาหรือร่วมมารดารับมรดกทั้งหมด แบ่ง {num_half_siblings} คน")

    # ลำดับ 5: ปู่ ย่า ตา ยาย
    elif num_grandparents > 0:
        citations.append("ป.พ.พ. มาตรา 1629(5)")
        if has_spouse:
            citations.append("ป.พ.พ. มาตรา 1635(3) (คู่สมรสได้รับสองในสามส่วน)")
            spouse_share = estate * (2.0 / 3.0)
            gp_share = estate * (1.0 / 3.0)
            shares["คู่สมรส"] = {"amount": spouse_share, "percent": 66.67, "heads": 1}
            shares["ปู่ ย่า ตา ยาย"] = {"amount": gp_share, "per_head": gp_share / num_grandparents, "percent": 33.33, "heads": num_grandparents}
            explanation_parts.append("ไม่มีลำดับ 1-4: คู่สมรสได้รับ 2/3 (66.67%) ปู่ย่าตายายแบ่ง 1/3 ที่เหลือ (33.33%)")
        else:
            each_share = estate / num_grandparents
            shares["ปู่ ย่า ตา ยาย"] = {"amount": estate, "per_head": each_share, "percent": 100.0, "heads": num_grandparents}
            explanation_parts.append(f"ปู่ ย่า ตา ยาย รับมรดกทั้งหมด แบ่ง {num_grandparents} คน")

    # ลำดับ 6: ลุง ป้า น้า อา
    elif num_uncles_aunts > 0:
        citations.append("ป.พ.พ. มาตรา 1629(6)")
        if has_spouse:
            citations.append("ป.พ.พ. มาตรา 1635(3) (คู่สมรสได้รับสองในสามส่วน)")
            spouse_share = estate * (2.0 / 3.0)
            ua_share = estate * (1.0 / 3.0)
            shares["คู่สมรส"] = {"amount": spouse_share, "percent": 66.67, "heads": 1}
            shares["ลุง ป้า น้า อา"] = {"amount": ua_share, "per_head": ua_share / num_uncles_aunts, "percent": 33.33, "heads": num_uncles_aunts}
            explanation_parts.append("ไม่มีลำดับ 1-5: คู่สมรสได้รับ 2/3 (66.67%) ลุงป้าน้าอาแบ่ง 1/3 ที่เหลือ (33.33%)")
        else:
            each_share = estate / num_uncles_aunts
            shares["ลุง ป้า น้า อา"] = {"amount": estate, "per_head": each_share, "percent": 100.0, "heads": num_uncles_aunts}
            explanation_parts.append(f"ลุง ป้า น้า อา รับมรดกทั้งหมด แบ่ง {num_uncles_aunts} คน")

    # ไม่มีทายาทโดยธรรม 6 ลำดับเลย
    else:
        if has_spouse:
            citations.append("ป.พ.พ. มาตรา 1635(4) (ไม่มีทายาทโดยธรรมลำดับอื่น คู่สมรสรับทั้งหมด)")
            shares["คู่สมรส"] = {"amount": estate, "percent": 100.0, "heads": 1}
            explanation_parts.append("ไม่มีญาติทายาทโดยธรรมลำดับ 1-6 คู่สมรสที่ยังมีชีวิตอยู่ได้รับมรดกทั้งหมด 100%")
        else:
            citations.append("ป.พ.พ. มาตรา 1753 (มรดกตกทอดแก่แผ่นดิน)")
            shares["แผ่นดิน (กระทรวงการคลัง)"] = {"amount": estate, "percent": 100.0, "heads": 1}
            explanation_parts.append("ไม่มีทายาทโดยธรรมและไม่มีคู่สมรส ทรัพย์มรดกตกทอดแก่แผ่นดินตาม ม.1753")

    return {
        "estate_value": estate,
        "shares": shares,
        "citations": citations,
        "explanation": " ".join(explanation_parts)
    }


def calculate_statute_of_limitations(case_type="criminal", penalty_years=0, is_compoundable=False,
                                     claim_type=None):
    """
    คำนวณอายุความทางอาญาและแพ่ง (ป.อ. ม.95, 96, ป.พ.พ. ม.193/30, 448)
    """
    citations = []
    limitation_years = 0
    limitation_months = 0
    critical_warning = None

    c_type = case_type.lower()
    if c_type in ["criminal", "อาญา"]:
        citations.append("ป.อ. มาตรา 95 (อายุความฟ้องคดีอาญา)")
        if is_compoundable:
            citations.append("ป.อ. มาตรา 96 (อายุความร้องทุกข์คดียอมความได้)")
            critical_warning = "[คำเตือน] ความผิดอันยอมความได้ ผู้เสียหายต้อง 'ร้องทุกข์หรือฟ้องร้องภายใน 3 เดือน' นับแต่วันที่รู้เรื่องความผิดและรู้ตัวผู้กระทำความผิด มิฉะนั้นคดีขาดอายุความทันทีตาม ป.อ. ม.96!"
            limitation_months = 3

        # กฎเกณฑ์ตาม ม.95
        p = float(penalty_years)
        if p >= 20 or p == -1: # -1 หมายถึง ประหารชีวิต/ตลอดชีวิต
            limitation_years = 20
        elif p > 7:
            limitation_years = 15
        elif p > 1:
            limitation_years = 10
        elif p > (1.0 / 12.0):
            limitation_years = 5
        else:
            limitation_years = 1

    elif c_type in ["civil", "แพ่ง"]:
        ct = (claim_type or "").lower()
        if "tort" in ct or "ละเมิด" in ct:
            citations.append("ป.พ.พ. มาตรา 448 (อายุความละเมิด)")
            limitation_years = 1
            critical_warning = "สิทธิเรียกร้องค่าเสียหายอันเกิดแต่มูลละเมิด ขาดอายุความเมื่อพ้น 1 ปีนับแต่วันที่ผู้เสียหายรู้ถึงการละเมิดและรู้ตัวผู้กระทำ หรือเมื่อพ้น 10 ปีนับแต่วันทำละเมิด"
        elif "loan" in ct or "กู้ยืม" in ct or "contract" in ct or "สัญญา" in ct:
            citations.append("ป.พ.พ. มาตรา 193/30 (อายุความทั่วไปแห่งหนี้)")
            limitation_years = 10
            critical_warning = "สัญญากู้ยืมเงินทั่วไปมีอายุความ 10 ปีนับแต่วันที่หนี้ถึงกำหนดชำระ (หากเป็นหนี้ผ่อนส่งเป็นงวดตาม ม.193/33 มีอายุความ 5 ปี)"
        elif "labor" in ct or "แรงงาน" in ct or "wage" in ct or "ค่าจ้าง" in ct:
            citations.append("ป.พ.พ. มาตรา 193/34(1) (สิทธิเรียกร้องค่าจ้างของลูกจ้าง)")
            limitation_years = 2
            critical_warning = "การเรียกร้องเอาเงินค่าจ้าง ค่าล่วงเวลา ค่าทำงานในวันหยุด มีอายุความ 2 ปี"
        else:
            citations.append("ป.พ.พ. มาตรา 193/30 (อายุความทั่วไป 10 ปี)")
            limitation_years = 10
            critical_warning = "อายุความแห่งสิทธิเรียกร้องทั่วไปที่มิได้กำหนดไว้เป็นอย่างอื่น มีกำหนด 10 ปี"

    return {
        "case_type": case_type,
        "limitation_years": limitation_years,
        "limitation_months": limitation_months,
        "is_compoundable": is_compoundable,
        "critical_warning": critical_warning,
        "citations": citations
    }


def calculate_severance_pay(tenure_months, monthly_wage, termination_reason="general"):
    """
    คำนวณค่าชดเชยการเลิกจ้างตาม พ.ร.บ. คุ้มครองแรงงาน พ.ศ. 2541 ม.118, 119
    """
    wage = float(monthly_wage)
    months = float(tenure_months)
    reason = str(termination_reason).lower()

    # ตรวจสอบข้อยกเว้นตาม ม.119 (ไม่ต้องจ่ายค่าชดเชย)
    section_119_reasons = ["misconduct", "fraud", "gross_negligence", "absence_3_days", "prison",
                           "ทุจริต", "จงใจ", "ประมาทเลินเล่อร้ายแรง", "ละทิ้งหน้าที่", "จำคุก"]
    for r in section_119_reasons:
        if r in reason:
            return {
                "tenure_months": months,
                "monthly_wage": wage,
                "severance_days": 0,
                "severance_amount": 0.0,
                "advance_notice_pay": 0.0,
                "is_exempt_section_119": True,
                "citations": ["พ.ร.บ. คุ้มครองแรงงาน พ.ศ. 2541 มาตรา 119"],
                "explanation": f"เลิกจ้างด้วยเหตุเข้าข้อยกเว้นตามมาตรา 119 ({termination_reason}) นายจ้างไม่ต้องจ่ายค่าชดเชยการเลิกจ้าง"
            }

    # คำนวณอัตราตาม ม.118
    # 120 วัน ~ 4 เดือน
    if months < 4:
        days = 0
        ratio = 0.0
    elif months < 12:  # 120 วัน ถึงไม่ครบ 1 ปี
        days = 30
        ratio = 1.0
    elif months < 36:  # 1 ปี ถึงไม่ครบ 3 ปี
        days = 90
        ratio = 3.0
    elif months < 72:  # 3 ปี ถึงไม่ครบ 6 ปี
        days = 180
        ratio = 6.0
    elif months < 120:  # 6 ปี ถึงไม่ครบ 10 ปี
        days = 240
        ratio = 8.0
    elif months < 240:  # 10 ปี ถึงไม่ครบ 20 ปี
        days = 300
        ratio = 10.0
    else:  # 20 ปีขึ้นไป
        days = 400
        ratio = 400.0 / 30.0

    severance_amount = wage * ratio
    advance_notice_pay = wage  # สินจ้างแทนการบอกกล่าวล่วงหน้า 1 งวดการจ่ายค่าจ้าง

    return {
        "tenure_months": months,
        "monthly_wage": wage,
        "severance_days": days,
        "severance_amount": round(severance_amount, 2),
        "advance_notice_pay": round(advance_notice_pay, 2),
        "is_exempt_section_119": False,
        "total_estimated": round(severance_amount + advance_notice_pay, 2),
        "citations": ["พ.ร.บ. คุ้มครองแรงงาน พ.ศ. 2541 มาตรา 118", "มาตรา 17 (สินจ้างแทนการบอกกล่าวล่วงหน้า)"],
        "explanation": f"อายุงาน {months:.1f} เดือน ได้รับค่าชดเชย {days} วัน (ประมาณ {ratio:.2f} เท่าของค่าจ้างรายเดือน) รวมเป็นเงิน {severance_amount:,.2f} บาท"
    }


def calculate_legal_interest(principal, start_date_str, end_date_str=None, custom_rate=None, interest_type="default"):
    """
    คำนวณดอกเบี้ยผิดนัดตาม ป.พ.พ. มาตรา 224 (แก้ไขใหม่ พ.ศ. 2564 อัตรา 5% ต่อปี)
    และตรวจสอบอัตราดอกเบี้ยเงินกู้สูงสุดตาม ม.654 (ไม่เกิน 15% ต่อปี หากเกินตกเป็นโมฆะทั้งหมด)
    """
    p = float(principal)
    if p <= 0:
        return {"error": "เงินต้นต้องมากกว่า 0"}

    # แปลงวันที่
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("start_date ต้องอยู่ในรูปแบบ YYYY-MM-DD")

    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except Exception:
            raise ValueError("end_date ต้องอยู่ในรูปแบบ YYYY-MM-DD")
    else:
        end_date = datetime.date.today()

    if end_date < start_date:
        raise ValueError("end_date ต้องไม่น้อยกว่า start_date")

    total_days = (end_date - start_date).days
    citations = ["ป.พ.พ. มาตรา 224 (แก้ไขเพิ่มเติม พ.ศ. 2564)"]
    breakdown = []
    total_interest = 0.0
    warning = None

    # กรณีมี custom rate (เช่น สัญญากู้ยืม)
    if custom_rate is not None:
        rate = float(custom_rate)
        if rate > 15.0 and interest_type == "loan":
            # ม.654 + พ.ร.บ.ห้ามเรียกดอกเบี้ยเกินอัตรา พ.ศ. 2560
            citations.append("ป.พ.พ. มาตรา 654 ประกอบ พ.ร.บ. ห้ามเรียกดอกเบี้ยเกินอัตรา พ.ศ. 2560")
            warning = "[คำเตือน] อัตราดอกเบี้ยเกินกว่าร้อยละ 15 ต่อปี ข้อตกลงดอกเบี้ยตกเป็นโมฆะทั้งหมดตามกฎหมาย! ผู้ให้กู้ไม่มีสิทธิคิดดอกเบี้ยได้แม้แต่บาทเดียว คงเรียกได้เฉพาะเงินต้นเท่านั้น"
            return {
                "principal": p,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "custom_rate": rate,
                "is_usurious": True,
                "total_days": total_days,
                "interest_amount": 0.0,
                "total_debt": p,
                "citations": citations,
                "warning": warning
            }
        else:
            interest = p * (rate / 100.0) * (total_days / 365.0)
            total_interest = interest
            breakdown.append({
                "period": f"{start_date} ถึง {end_date}",
                "days": total_days,
                "rate_percent": rate,
                "interest": round(interest, 2)
            })
    else:
        # ดอกเบี้ยผิดนัดตามกฎหมาย
        # วันที่กฎหมายใหม่มีผลบังคับใช้: 11 เมษายน 2564 (2021-04-11)
        AMENDMENT_DATE = datetime.date(2021, 4, 11)

        # ช่วงที่ 1: ก่อน 11 เม.ย. 2564 (อัตราเดิม 7.5% ต่อปี)
        if start_date < AMENDMENT_DATE:
            period1_end = min(end_date, AMENDMENT_DATE)
            days1 = (period1_end - start_date).days
            if days1 > 0:
                int1 = p * 0.075 * (days1 / 365.0)
                total_interest += int1
                breakdown.append({
                    "period": f"{start_date} ถึง {period1_end} (ก่อน พ.ร.ก. แก้ไข)",
                    "days": days1,
                    "rate_percent": 7.5,
                    "interest": round(int1, 2)
                })

        # ช่วงที่ 2: ตั้งแต่ 11 เม.ย. 2564 เป็นต้นไป (อัตราใหม่ 5.0% ต่อปี)
        if end_date >= AMENDMENT_DATE:
            period2_start = max(start_date, AMENDMENT_DATE)
            days2 = (end_date - period2_start).days
            if days2 > 0:
                int2 = p * 0.05 * (days2 / 365.0)
                total_interest += int2
                breakdown.append({
                    "period": f"{period2_start} ถึง {end_date} (กฎหมายใหม่ ม.224)",
                    "days": days2,
                    "rate_percent": 5.0,
                    "interest": round(int2, 2)
                })

    return {
        "principal": p,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "total_days": total_days,
        "breakdown": breakdown,
        "total_interest": round(total_interest, 2),
        "interest_amount": round(total_interest, 2),
        "total_debt": round(p + total_interest, 2),
        "citations": citations,
        "warning": warning or "ป.พ.พ. มาตรา 224 วรรคสอง ห้ามมิให้คิดดอกเบี้ยซ้อนดอกเบี้ย (ห้ามทบต้น) ในระหว่างผิดนัด"
    }


def check_evidence_admissibility(
    dispute_type="loan",
    amount=0.0,
    evidence_type="paper_signed",
    has_written_evidence=False,
    has_signature=False,
    is_electronic=False,
    electronic_details=None,
    exceptions_claimed=None
):
    """
    Evidence Admissibility Engine (ตาม ป.วิ.พ. ม.94 และ พ.ร.บ.ว่าด้วยธุรกรรมทางอิเล็กทรอนิกส์ พ.ศ. 2544)
    ตรวจสอบความสามารถในการรับฟังพยานหลักฐาน, ข้อห้าม Parol Evidence Rule, ข้อยกเว้น ม.94 วรรคท้าย และ ม.93(2),
    รวมถึงความสมบูรณ์ของพยานหลักฐานอิเล็กทรอนิกส์ตามกฎหมาย
    """
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        amount = 0.0

    dt = str(dispute_type).lower().strip()
    et = str(evidence_type).lower().strip()

    if exceptions_claimed is None:
        exceptions = []
    elif isinstance(exceptions_claimed, list):
        exceptions = [str(x).lower().strip() for x in exceptions_claimed]
    else:
        exceptions = [str(exceptions_claimed).lower().strip()]

    e_details = electronic_details if isinstance(electronic_details, dict) else {}

    # Normalize boolean flags
    if et in ("paper_signed", "written_signed", "สัญญาเป็นหนังสือ", "สัญญากู้ยืมเงิน"):
        has_written_evidence = True
        has_signature = True
    elif et in ("written_unsigned", "หนังสือไม่ลงชื่อ"):
        has_written_evidence = True
        has_signature = False
    elif et in ("electronic_chat", "line_chat", "screenshot_slip", "แชท", "แชทไลน์", "ข้อความอิเล็กทรอนิกส์"):
        is_electronic = True

    # Map display names
    display_names = {
        "loan": "การกู้ยืมเงิน (Loan Dispute)",
        "borrowing": "การกู้ยืมเงิน (Loan Dispute)",
        "suretyship": "การค้ำประกัน (Suretyship Dispute)",
        "guarantee": "การค้ำประกัน (Suretyship Dispute)",
        "lease": "การเช่าอสังหาริมทรัพย์ (Lease Dispute)",
        "rent": "การเช่าอสังหาริมทรัพย์ (Lease Dispute)",
        "sale_immovable": "สัญญาจะซื้อจะขายอสังหาริมทรัพย์ (Immovable Property Sale)",
        "sale": "สัญญาซื้อขาย (Sale of Goods/Property)",
        "general_civil": "ข้อพิพาททางแพ่งทั่วไป (General Civil Dispute)",
        "tort": "มูลความรับผิดเพื่อละเมิด (Tort Claim)",
        "criminal": "คดีอาญา (Criminal Proceeding)"
    }
    dispute_display = display_names.get(dt, f"ข้อพิพาท: {dispute_type}")

    # Initialize results
    status = "ADMISSIBLE"
    admissible = True
    probative_weight = "HIGH"
    statutory_barrier = None
    applicable_sections = []
    precedents = []
    analysis = ""
    exceptions_applied = []
    recommendations = []

    # 1. Exception Check: Force Majeure Lost/Destroyed Document (ป.วิ.พ. ม.93(2))
    lost_keywords = ["force_majeure_lost", "lost", "destroyed", "สูญหาย", "เหตุสุดวิสัย", "เอกสารสูญหาย"]
    if any(k in ex for ex in exceptions for k in lost_keywords):
        status = "CONDITIONALLY_ADMISSIBLE"
        admissible = True
        probative_weight = "MEDIUM"
        statutory_barrier = "ป.วิ.พ. มาตรา 93(2) (ข้อยกเว้นกรณีเอกสารสูญหายหรือถูกทำลายโดยเหตุสุดวิสัย)"
        applicable_sections = ["ป.วิ.พ. มาตรา 93(2)", "ป.วิ.พ. มาตรา 94"]
        precedents = ["ฎีกาที่ 1386/2531", "ฎีกาที่ 2084/2537"]
        exceptions_applied.append("ป.วิ.พ. มาตรา 93(2): ต้นฉบับเอกสารสูญหายหรือถูกทำลายโดยเหตุสุดวิสัย หรือไม่สามารถนำต้นฉบับมาแสดงได้โดยมิใช่ความผิดของผู้ขอนำสืบ")
        analysis = (
            "ตาม ป.วิ.พ. มาตรา 93(2) กรณีที่ต้นฉบับเอกสารสูญหายหรือถูกทำลายโดยเหตุสุดวิสัย "
            "กฎหมายเปิดช่องให้คู่ความสามารถนำสำเนาเอกสารหรือนำพยานบุคคลเข้าสืบแทนต้นฉบับเอกสารได้ "
            "โดยผู้ขอนำสืบมีภาระต้องนำสืบแสดงต่อศาลให้เห็นถึงความมีอยู่เดิมของต้นฉบับ และเหตุสุดวิสัยที่ทำให้ต้นฉบับสูญหายโดยสุจริตเสียก่อน"
        )
        recommendations = [
            "ยื่นคำร้องต่อศาลแสดงเหตุจำเป็นและขออนุญาตนำสืบพยานบุคคลหรือสำเนาเอกสารตาม ป.วิ.พ. ม.93(2)",
            "เตรียมพยานหลักฐานยืนยันเหตุสุดวิสัย เช่น บันทึกประจำวันแจ้งความเอกสารสูญหาย หรือหลักฐานการเกิดอัคคีภัย/อุทกภัย",
            "นำพยานบุคคลที่รู้เห็นการทำสัญญาหรือเห็นต้นฉบับเอกสารเดิมมาเบิกความสนับสนุน"
        ]
        return {
            "dispute_type": dt,
            "dispute_type_display": dispute_display,
            "amount": amount,
            "evidence_type": et,
            "admissible": admissible,
            "status": status,
            "probative_weight": probative_weight,
            "statutory_barrier": statutory_barrier,
            "applicable_sections": applicable_sections,
            "precedents": precedents,
            "analysis": analysis,
            "exceptions_applied": exceptions_applied,
            "recommendations": recommendations
        }

    # 2. Exception Check: Parol Evidence Rule Exceptions (ป.วิ.พ. ม.94 วรรคท้าย)
    sham_keywords = ["no_consideration", "sham_transaction", "void", "fraud", "mistake", "duress",
                     "ไม่มีการส่งมอบเงิน", "นิติกรรมอำพราง", "กลฉ้อฉล", "สำคัญผิด", "ข่มขู่", "สัญญาปลอม", "ไม่มีมูลหนี้"]
    if any(k in ex for ex in exceptions for k in sham_keywords):
        status = "CONDITIONALLY_ADMISSIBLE"
        admissible = True
        probative_weight = "MEDIUM"
        statutory_barrier = "ป.วิ.พ. มาตรา 94 วรรคท้าย (ข้อยกเว้นการสืบพยานบุคคลหักล้างเอกสาร)"
        applicable_sections = ["ป.วิ.พ. มาตรา 94 วรรคท้าย", "ป.พ.พ. มาตรา 650 วรรคสอง", "ป.พ.พ. มาตรา 155"]
        precedents = ["ฎีกาที่ 4101/2562", "ฎีกาที่ 8477/2563"]
        exceptions_applied.append("ป.วิ.พ. มาตรา 94 วรรคท้าย: นำสืบว่าเอกสารเป็นเอกสารปลอม สัญญาไม่สมบูรณ์ หรือไม่มีมูลหนี้ที่แท้จริง (ไม่มีการส่งมอบเงินกู้จริง)")
        analysis = (
            "ตาม ป.วิ.พ. มาตรา 94 วรรคท้าย บทบัญญัติแห่งมาตรา 94 มิให้ใช้บังคับในการที่คู่ความนำสืบพยานบุคคลว่า "
            "สัญญาเป็นนิติกรรมอำพราง สัญญาไม่สมบูรณ์ หรือไม่มีมูลหนี้แท้จริง โดยเฉพาะการกู้ยืมเงินซึ่งย่อมสมบูรณ์ต่อเมื่อมีการส่งมอบทรัพย์สินตาม ป.พ.พ. มาตรา 650 วรรคสอง "
            "การนำสืบพยานบุคคลว่าผู้ให้กู้มิได้ส่งมอบเงินตามสัญญาจึงมิใช่เป็นการนำสืบแก้ไขเปลี่ยนแปลงเอกสาร แต่เป็นการสืบว่าสัญญาไม่สมบูรณ์ ศาลจึงรับฟังพยานบุคคลได้ "
            "ตามแนวบรรทัดฐานคำพิพากษาศาลฎีกาที่ 4101/2562 และ 8477/2563"
        )
        recommendations = [
            "นำสืบพยานบุคคลและพยานหลักฐานแวดล้อมเพื่อหักล้างมูลหนี้ว่ามิได้มีการส่งมอบเงินกู้จริง",
            "ขอให้ศาลมีหมายเรียกรายการเดินบัญชี (Bank Statement) ของคู่สัญญามาตรวจสอบว่ามีการเคลื่อนไหวของเงินจริงหรือไม่",
            "ยกข้อต่อสู้เรื่องนิติกรรมอำพรางหรือความไม่สมบูรณ์แห่งสัญญาไว้ในคำให้การแก้ฟ้องอย่างชัดแจ้ง"
        ]
        return {
            "dispute_type": dt,
            "dispute_type_display": dispute_display,
            "amount": amount,
            "evidence_type": et,
            "admissible": admissible,
            "status": status,
            "probative_weight": probative_weight,
            "statutory_barrier": statutory_barrier,
            "applicable_sections": applicable_sections,
            "precedents": precedents,
            "analysis": analysis,
            "exceptions_applied": exceptions_applied,
            "recommendations": recommendations
        }

    # 3. Criminal Case Branch
    if dt in ("criminal", "อาญา", "คดีอาญา"):
        status = "ADMISSIBLE"
        admissible = True
        probative_weight = "HIGH"
        statutory_barrier = None
        applicable_sections = ["ป.วิ.อ. มาตรา 226", "ป.วิ.อ. มาตรา 227"]
        analysis = (
            "ในกระบวนการพิจารณาคดีอาญา ไม่อยู่ภายใต้ข้อห้ามตาม ป.วิ.พ. มาตรา 94 ศาลใช้ระบบเสรีในการรับฟังพยานหลักฐานตาม ป.วิ.อ. มาตรา 226 "
            "สามารถนำสืบพยานบุคคล พยานวัตถุ พยานแวดล้อม และพยานอิเล็กทรอนิกส์ได้ทุกประเภท โดยศาลจะวินิจฉัยชั่งน้ำหนักพยานหลักฐานตามหลักเหตุและผล "
            "และหากมีความสงสัยตามสมควร ศาลจะยกประโยชน์แห่งความสงสัยให้แก่จำเลยตาม ป.วิ.อ. มาตรา 227"
        )
        recommendations = [
            "รวบรวมพยานหลักฐานโดยชอบด้วยกฎหมายตาม ป.วิ.อ. ม.226 เพื่อป้องกันมิให้ถูกตัดเป็นพยานหลักฐานที่ได้มาโดยมิชอบตาม ม.226/1",
            "ตรวจสอบสายการครอบครองพยานหลักฐาน (Chain of Custody) ของพยานดิจิทัลให้ชัดเจน"
        ]

    # 4. General Civil / Tort Branch
    elif dt in ("general_civil", "tort", "แพ่งทั่วไป", "ละเมิด"):
        status = "ADMISSIBLE"
        admissible = True
        probative_weight = "HIGH" if (has_written_evidence or is_electronic) else "MEDIUM"
        statutory_barrier = None
        applicable_sections = ["ป.วิ.พ. มาตรา 84 (หน้าที่นำสืบ)", "ป.พ.พ. มาตรา 420"]
        analysis = (
            "ข้อพิพาททางแพ่งทั่วไปหรือมูลหนี้ละเมิด กฎหมายมิได้บัญญัติบังคับว่าต้องมีพยานเอกสารเป็นหนังสือ "
            "จึงไม่อยู่ในข้อจำกัดของ Parol Evidence Rule ตาม ป.วิ.พ. มาตรา 94 คู่ความมีสิทธินำพยานบุคคล พยานเอกสาร หรือพยานวัตถุเข้าสืบพิสูจน์ "
            "ตามหลักภาระการพิสูจน์แห่ง ป.วิ.พ. มาตรา 84"
        )
        recommendations = [
            "รวบรวมพยานแวดล้อม ภาพถ่าย กล้องวงจรปิด หรือพยานบุคคลในสถานที่เกิดเหตุ",
            "จัดทำรายงานประเมินความเสียหายอย่างเป็นทางการเพื่อเพิ่มน้ำหนักในการเรียกค่าสินไหมทดแทน"
        ]

    # 5. Loan Dispute Branch (ป.พ.พ. ม.653 + ป.วิ.พ. ม.94 + พ.ร.บ.ธุรกรรมอิเล็กทรอนิกส์)
    elif dt in ("loan", "borrowing", "กู้ยืม", "กู้ยืมเงิน"):
        if amount <= 2000.0:
            status = "ADMISSIBLE"
            admissible = True
            probative_weight = "MEDIUM"
            statutory_barrier = None
            applicable_sections = ["ป.พ.พ. มาตรา 653 วรรคหนึ่ง", "ป.วิ.พ. มาตรา 94"]
            analysis = (
                "การกู้ยืมเงินเป็นจำนวนเงินไม่เกิน 2,000 บาท กฎหมายมิได้บังคับให้ต้องมีหลักฐานแห่งการกู้ยืมเป็นหนังสือลงลายมือชื่อผู้ยืม (ป.พ.พ. มาตรา 653 วรรคหนึ่ง) "
                "จึงไม่อยู่ในข้อห้ามนำสืบพยานบุคคลตาม ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก) เจ้าหนี้สามารถนำพยานบุคคลเข้าสืบพิสูจน์การกู้ยืมเงินและฟ้องร้องบังคับคดีได้โดยชอบ"
            )
            recommendations = [
                "นำพยานบุคคลที่รู้เห็นการตกลงยืมและการส่งมอบเงินเข้าเบิกความต่อศาล",
                "หากมีหลักฐานการโอนเงินหรือข้อความทวงถาม ให้นำเข้าสืบประกอบเพื่อยกระดับน้ำหนักการรับฟัง"
            ]
        else:
            # Amount > 2000 THB
            if is_electronic:
                platform = e_details.get("platform", "LINE / ข้อความทางสื่อสังคมออนไลน์")
                has_slip = e_details.get("has_bank_slip", False) or et == "screenshot_slip" or "slip" in et
                status = "ADMISSIBLE"
                admissible = True
                probative_weight = "HIGH" if has_slip else "MEDIUM"
                statutory_barrier = None
                applicable_sections = [
                    "พ.ร.บ.ว่าด้วยธุรกรรมทางอิเล็กทรอนิกส์ พ.ศ. 2544 มาตรา 7, 8, 9, 11, 12",
                    "ป.พ.พ. มาตรา 650 วรรคสอง (การส่งมอบทรัพย์สิน)",
                    "ป.พ.พ. มาตรา 653 วรรคหนึ่ง (หลักฐานเป็นหนังสือ)",
                    "ป.วิ.พ. มาตรา 94"
                ]
                precedents = ["ฎีกาที่ 6745/2562", "ฎีกาที่ 8089/2556", "ฎีกาที่ 2772/2565"]
                analysis = (
                    f"การสนทนาขอกู้ยืมเงินผ่านสื่ออิเล็กทรอนิกส์ ({platform}) ถือเป็นข้อมูลอิเล็กทรอนิกส์ที่มีผลผูกพันตาม พ.ร.บ.ธุรกรรมทางอิเล็กทรอนิกส์ฯ ม.7 "
                    "และรับฟังเป็นหลักฐานแห่งการกู้ยืมเป็นหนังสือได้ตาม ม.8 โดยชื่อบัญชีผู้ใช้ (User Account / Profile) ที่เชื่อมโยงกับตัวบุคคลถือเป็นการลงลายมือชื่ออิเล็กทรอนิกส์ตาม ม.9 "
                    "ภาพถ่ายหน้าจอ (Screenshot) และเอกสารการพิมพ์ออก รับฟังได้เสมือนต้นฉบับตาม ม.11 และ ม.12 เมื่อประกอบกับหลักฐานสลิปโอนเงินผ่านระบบธนาคาร (Mobile Banking) "
                    "เพื่อพิสูจน์การส่งมอบเงินกู้ตาม ป.พ.พ. ม.650 วรรคสอง จึงมีองค์ประกอบครบถ้วนตาม ป.พ.พ. ม.653 วรรคหนึ่ง ศาลรับฟังได้และมีน้ำหนักรับฟังสูง "
                    "ตามแนวคำพิพากษาศาลฎีกาที่ 6745/2562 และ 2772/2565"
                )
                recommendations = [
                    "พิมพ์ภาพหน้าจอการสนทนาขอกู้เงินให้เห็นชื่อบัญชี วันที่ เวลา และข้อความขอยืมอย่างชัดเจนต่อเนื่อง",
                    "แนบสลิปโอนเงินจาก Mobile Banking ที่ระบุเลขอ้างอิง ชื่อผู้โอน-ผู้รับ และวันเวลาทำรายการ",
                    "ขอเอกสารรายการเดินบัญชี (Statement) จากธนาคารเพื่อรับรองความถูกต้องของธุรกรรม",
                    "ตรวจสอบข้อมูลบัญชีผู้ใช้ให้สามารถเชื่อมโยงถึงหมายเลขโทรศัพท์หรือตัวบุคคลจริงของจำเลย",
                    "ทำหนังสือบอกกล่าวทวงถาม (Notice) พร้อมกำหนดเวลาชำระหนี้ตาม ป.พ.พ. ม.204 ก่อนยื่นฟ้อง"
                ]
            elif has_written_evidence and has_signature:
                status = "ADMISSIBLE"
                admissible = True
                probative_weight = "HIGH"
                statutory_barrier = None
                applicable_sections = ["ป.พ.พ. มาตรา 653 วรรคหนึ่ง", "ป.วิ.พ. มาตรา 94", "ประมวลรัษฎากร มาตรา 118"]
                analysis = (
                    "มีหลักฐานแห่งการกู้ยืมเป็นหนังสือลงลายมือชื่อผู้ยืมเป็นสำคัญ ครบถ้วนตามเงื่อนไขของ ป.พ.พ. มาตรา 653 วรรคหนึ่ง "
                    "สามารถนำสืบพยานเอกสารและฟ้องร้องบังคับคดีได้สมบูรณ์ ไม่ติดข้อห้ามตาม ป.วิ.พ. มาตรา 94"
                )
                recommendations = [
                    "นำส่งต้นฉบับเอกสารสัญญากู้ยืมเงินต่อศาลตาม ป.วิ.พ. มาตรา 93",
                    "นำสืบหลักฐานการส่งมอบเงินกู้ตาม ป.พ.พ. มาตรา 650 วรรคสอง เพื่อยืนยันว่าสัญญากู้บริบูรณ์",
                    "ตรวจสอบการปิดอากรแสตมป์ตามประมวลรัษฎากร มาตรา 118 (บัญชีอัตราอากรแสตมป์ ลักษณะ 5: กู้ยืมเงิน ปิดอากร 1 บาท ต่อทุก 2,000 บาท เศษปัดขึ้น สูงสุดไม่เกิน 10,000 บาท) มิฉะนั้นจะตกเป็นเอกสารต้องห้ามรับฟังในคดีแพ่ง"
                ]
            elif has_written_evidence and not has_signature:
                status = "INADMISSIBLE"
                admissible = False
                probative_weight = "NONE"
                statutory_barrier = "ป.พ.พ. มาตรา 653 วรรคหนึ่ง ประกอบ ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"
                applicable_sections = ["ป.พ.พ. มาตรา 653 วรรคหนึ่ง", "ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"]
                analysis = (
                    "เอกสารสัญญากู้ยืมเงินขาดการลงลายมือชื่อของผู้ยืม จึงไม่ครบองค์ประกอบแห่งหลักฐานเป็นหนังสือตาม ป.พ.พ. มาตรา 653 วรรคหนึ่ง "
                    "และต้องห้ามมิให้นำพยานบุคคลเข้าสืบว่ามีการกู้ยืมเงินตาม ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก) ไม่อาจฟ้องร้องบังคับคดีได้"
                )
                recommendations = [
                    "เจรจาให้ลูกหนี้ลงลายมือชื่อในหนังสือรับสภาพหนี้ หรือทำสัญญาประนีประนอมยอมความใหม่",
                    "ส่งข้อความสอบถามและยืนยันยอดหนี้ผ่านแชทอิเล็กทรอนิกส์ เพื่อสร้างหลักฐานลายมือชื่ออิเล็กทรอนิกส์ใหม่ตาม พ.ร.บ.ธุรกรรมฯ ม.8 และ ม.9"
                ]
            else:
                # Oral only for Loan > 2000 THB
                status = "INADMISSIBLE"
                admissible = False
                probative_weight = "NONE"
                statutory_barrier = "ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก) ประกอบ ป.พ.พ. มาตรา 653 วรรคหนึ่ง"
                applicable_sections = ["ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)", "ป.พ.พ. มาตรา 653 วรรคหนึ่ง"]
                precedents = ["ฎีกาที่ 6745/2562 (เปรียบเทียบกรณีมีหลักฐานอิเล็กทรอนิกส์)", "ฎีกาที่ 4101/2562"]
                analysis = (
                    f"การกู้ยืมเงินจำนวน {amount:,.2f} บาท เกินกว่า 2,000 บาท กฎหมายบังคับว่าต้องมีหลักฐานแห่งการกู้ยืมเป็นหนังสือลงลายมือชื่อผู้ยืมเป็นสำคัญ จึงจะฟ้องร้องบังคับคดีได้ (ป.พ.พ. ม.653 วรรคหนึ่ง) "
                    "เมื่อไม่มีพยานเอกสารหรือข้อมูลอิเล็กทรอนิกส์ จึงต้องห้ามมิให้นำพยานบุคคลเข้าสืบตาม ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก) หากนำคดีขึ้นสู่ศาล ศาลต้องพิพากษายกฟ้อง"
                )
                recommendations = [
                    "ห้ามฟ้องร้องคดีโดยอาศัยเพียงพยานบุคคล เพราะศาลจะพิพากษายกฟ้องเนื่องจากต้องห้ามตาม ป.วิ.พ. ม.94",
                    "ส่งข้อความทวงถามทางแชท (LINE/Facebook/SMS) ให้ลูกหนี้ตอบรับยอมรับยอดหนี้ เพื่อสร้างหลักฐานเป็นหนังสืออิเล็กทรอนิกส์ตาม พ.ร.บ.ธุรกรรมฯ ม.8 และ ม.9",
                    "นัดหมายทำหนังสือรับสภาพหนี้ (Acknowledgment of Debt) หรือทำสัญญาประนีประนอมยอมความ",
                    "หากลูกหนี้มีการโอนเงินคืนบางส่วน ให้เก็บสลิปการชำระหนี้ไว้เพื่อใช้ประกอบการนำสืบรับสภาพหนี้ตาม ป.พ.พ. ม.193/14"
                ]

    # 6. Suretyship Dispute Branch
    elif dt in ("suretyship", "guarantee", "ค้ำประกัน"):
        if (has_written_evidence and has_signature) or et in ("paper_signed", "written_signed"):
            status = "ADMISSIBLE"
            admissible = True
            probative_weight = "HIGH"
            statutory_barrier = None
            applicable_sections = ["ป.พ.พ. มาตรา 680 วรรคสอง", "ป.พ.พ. มาตรา 681/1", "ป.วิ.พ. มาตรา 94"]
            analysis = (
                "สัญญาค้ำประกันมีหลักฐานเป็นหนังสือลงลายมือชื่อผู้ค้ำประกันเป็นสำคัญ ถูกต้องตาม ป.พ.พ. มาตรา 680 วรรคสอง "
                "สามารถนำสืบพยานเอกสารและฟ้องร้องบังคับคดีได้ ทั้งนี้ต้องตรวจสอบว่ามิได้มีข้อตกลงให้ผู้ค้ำประกันรับผิดอย่างลูกหนี้ร่วมตาม ม.681/1 ซึ่งตกเป็นโมฆะ"
            )
            recommendations = [
                "ตรวจสอบเนื้อหาในสัญญาค้ำประกันว่าไม่มีข้อความขัดต่อ ป.พ.พ. ม.681/1 (ห้ามทำสัญญาค้ำประกันแบบลูกหนี้ร่วม)",
                "ทำหนังสือบอกกล่าวไปยังผู้ค้ำประกันภายใน 60 วัน นับแต่วันที่ลูกหนี้ผิดนัดตาม ป.พ.พ. ม.686"
            ]
        else:
            status = "INADMISSIBLE"
            admissible = False
            probative_weight = "NONE"
            statutory_barrier = "ป.พ.พ. มาตรา 680 วรรคสอง ประกอบ ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"
            applicable_sections = ["ป.พ.พ. มาตรา 680 วรรคสอง", "ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"]
            analysis = (
                "สัญญาค้ำประกันกฎหมายบังคับว่าต้องมีหลักฐานเป็นหนังสือลงลายมือชื่อผู้ค้ำประกันเป็นสำคัญ มิฉะนั้นจะฟ้องร้องบังคับคดีไม่ได้ตาม ป.พ.พ. มาตรา 680 วรรคสอง "
                "การตกลงค้ำประกันด้วยวาจาจึงต้องห้ามมิให้นำพยานบุคคลเข้าสืบตาม ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"
            )
            recommendations = [
                "ไม่สามารถฟ้องร้องผู้ค้ำประกันด้วยวาจาได้ ต้องจัดทำสัญญาค้ำประกันเป็นหนังสือลงลายมือชื่อผู้ค้ำประกันให้ถูกต้อง"
            ]

    # 7. Lease Dispute Branch
    elif dt in ("lease", "rent", "เช่า", "เช่าทรัพย์", "เช่าอสังหาริมทรัพย์"):
        if (has_written_evidence and has_signature) or et in ("paper_signed", "written_signed"):
            lease_years = float(e_details.get("lease_years", 1))
            registered = e_details.get("registered", False)
            if lease_years > 3 and not registered:
                status = "CONDITIONALLY_ADMISSIBLE"
                admissible = True
                probative_weight = "MEDIUM"
                statutory_barrier = "ป.พ.พ. มาตรา 538 (จำกัดการบังคับคดีได้เพียง 3 ปี)"
                applicable_sections = ["ป.พ.พ. มาตรา 538", "ป.วิ.พ. มาตรา 94"]
                analysis = (
                    "การเช่าอสังหาริมทรัพย์ที่มีกำหนดเวลาเกินกว่า 3 ปี หากทำเป็นหนังสือลงลายมือชื่อคู่สัญญาแต่ไม่ได้จดทะเบียนต่อพนักงานเจ้าหน้าที่ "
                    "ตาม ป.พ.พ. มาตรา 538 ฟ้องร้องบังคับคดีได้เพียง 3 ปีเท่านั้น"
                )
                recommendations = [
                    "นำสัญญาเช่าไปจดทะเบียนต่อพนักงานเจ้าหน้าที่สำนักงานที่ดินเพื่อให้มีผลบังคับครบตลอดอายุสัญญาเช่า"
                ]
            else:
                status = "ADMISSIBLE"
                admissible = True
                probative_weight = "HIGH"
                statutory_barrier = None
                applicable_sections = ["ป.พ.พ. มาตรา 538", "ป.วิ.พ. มาตรา 94"]
                analysis = (
                    "สัญญาเช่าอสังหาริมทรัพย์มีหลักฐานเป็นหนังสือลงลายมือชื่อฝ่ายที่ต้องรับผิดเป็นสำคัญ ครบถ้วนตาม ป.พ.พ. มาตรา 538 "
                    "สามารถนำสืบพยานเอกสารและฟ้องร้องบังคับคดีได้สมบูรณ์"
                )
                recommendations = [
                    "นำสืบสัญญาเช่าต้นฉบับและหลักฐานการชำระค่าเช่าหรือการครอบครองทรัพย์สินที่เช่า"
                ]
        else:
            status = "INADMISSIBLE"
            admissible = False
            probative_weight = "NONE"
            statutory_barrier = "ป.พ.พ. มาตรา 538 ประกอบ ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"
            applicable_sections = ["ป.พ.พ. มาตรา 538", "ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"]
            analysis = (
                "การเช่าอสังหาริมทรัพย์ หากไม่มีหลักฐานเป็นหนังสือลงลายมือชื่อฝ่ายที่ต้องรับผิด ย่อมฟ้องร้องบังคับคดีไม่ได้ตาม ป.พ.พ. มาตรา 538 "
                "และต้องห้ามมิให้นำสืบพยานบุคคลตาม ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"
            )
            recommendations = [
                "จัดทำสัญญาเช่าเป็นหนังสือลงลายมือชื่อผู้เช่าและผู้ให้เช่า"
            ]

    # 8. Sale of Immovable Dispute Branch
    elif dt in ("sale_immovable", "sale", "จะซื้อจะขาย", "ซื้อขายอสังหาริมทรัพย์"):
        deposit_keywords = ["deposit_paid", "part_performance", "มัดจำ", "วางประจำ", "ชำระหนี้บางส่วน"]
        if any(k in ex for ex in exceptions for k in deposit_keywords) or e_details.get("has_deposit", False):
            status = "ADMISSIBLE"
            admissible = True
            probative_weight = "HIGH"
            statutory_barrier = None
            applicable_sections = ["ป.พ.พ. มาตรา 456 วรรคสอง", "ป.พ.พ. มาตรา 378 (มัดจำ)", "ป.วิ.พ. มาตรา 94"]
            analysis = (
                "สัญญาจะซื้อจะขายอสังหาริมทรัพย์ แม้มิได้ทำหลักฐานเป็นหนังสือ แต่เมื่อมีการวางประจำ (วางมัดจำตาม ม.378) "
                "หรือมีการชำระหนี้บางส่วน ย่อมเข้าข้อยกเว้นตาม ป.พ.พ. มาตรา 456 วรรคสอง สามารถฟ้องร้องบังคับคดีได้โดยชอบ และนำพยานบุคคลเข้าสืบพิสูจน์ได้"
            )
            recommendations = [
                "นำสืบหลักฐานการวางมัดจำ สลิปโอนเงิน หรือใบเสร็จรับเงิน เพื่อพิสูจน์การวางประจำตาม ป.พ.พ. ม.456 วรรคสอง"
            ]
        elif (has_written_evidence and has_signature) or et in ("paper_signed", "written_signed"):
            status = "ADMISSIBLE"
            admissible = True
            probative_weight = "HIGH"
            statutory_barrier = None
            applicable_sections = ["ป.พ.พ. มาตรา 456 วรรคสอง", "ป.วิ.พ. มาตรา 94"]
            analysis = (
                "สัญญาจะซื้อจะขายอสังหาริมทรัพย์มีหลักฐานเป็นหนังสือลงลายมือชื่อฝ่ายที่ต้องรับผิดเป็นสำคัญ ครบถ้วนตาม ป.พ.พ. มาตรา 456 วรรคสอง "
                "สามารถฟ้องร้องบังคับคดีให้โอนกรรมสิทธิ์ได้สมบูรณ์"
            )
            recommendations = [
                "นำสืบต้นฉบับสัญญาจะซื้อจะขายและหลักฐานการนัดหมายโอนกรรมสิทธิ์ ณ สำนักงานที่ดิน"
            ]
        else:
            status = "INADMISSIBLE"
            admissible = False
            probative_weight = "NONE"
            statutory_barrier = "ป.พ.พ. มาตรา 456 วรรคสอง ประกอบ ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"
            applicable_sections = ["ป.พ.พ. มาตรา 456 วรรคสอง", "ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"]
            analysis = (
                "สัญญาจะซื้อจะขายอสังหาริมทรัพย์ที่ตกลงกันด้วยวาจา โดยมิได้มีหลักฐานเป็นหนังสือ มิได้วางประจำ และมิได้ชำระหนี้บางส่วน "
                "ย่อมฟ้องร้องบังคับคดีไม่ได้ตาม ป.พ.พ. มาตรา 456 วรรคสอง และต้องห้ามมิให้นำสืบพยานบุคคลตาม ป.วิ.พ. มาตรา 94 วรรคหนึ่ง (ก)"
            )
            recommendations = [
                "ไม่สามารถฟ้องร้องบังคับคดีได้ เว้นแต่จะมีการชำระเงินหรือวางมัดจำและมีหลักฐานการโอนเงินเพื่อเข้าข้อยกเว้นตาม ม.456 วรรคสอง"
            ]

    # Default fallback
    else:
        status = "ADMISSIBLE" if (has_written_evidence or is_electronic) else "CONDITIONALLY_ADMISSIBLE"
        admissible = True
        probative_weight = "MEDIUM"
        statutory_barrier = None
        applicable_sections = ["ป.วิ.พ. มาตรา 84"]
        analysis = "ข้อพิพาทไม่อยู่ในกลุ่มที่กฎหมายกำหนดแบบหรือบังคับพยานเอกสารเป็นการเฉพาะ สามารถนำสืบพยานหลักฐานได้ตามกระบวนพิจารณาความแพ่งทั่วไป"
        recommendations = ["รวบรวมพยานหลักฐานทุกชนิดที่เกี่ยวข้องเพื่อสนับสนุนภาระการพิสูจน์"]

    return {
        "dispute_type": dt,
        "dispute_type_display": dispute_display,
        "amount": amount,
        "evidence_type": et,
        "admissible": admissible,
        "status": status,
        "probative_weight": probative_weight,
        "statutory_barrier": statutory_barrier,
        "applicable_sections": applicable_sections,
        "precedents": precedents,
        "analysis": analysis,
        "exceptions_applied": exceptions_applied,
        "recommendations": recommendations
    }


def format_evidence_admissibility(res):
    lines = []
    lines.append("[ผลการตรวจสอบความสามารถในการรับฟังพยานหลักฐาน (Evidence Admissibility Engine)]")
    lines.append(f"   ประเภทข้อพิพาท: {res.get('dispute_type_display', res.get('dispute_type'))}")
    if res.get('amount', 0) > 0:
        lines.append(f"   มูลค่าข้อพิพาท: {res['amount']:,.2f} บาท")
    lines.append(f"   สถานะการรับฟัง: {res.get('status')} ({'รับฟังได้' if res.get('admissible') else 'รับฟังไม่ได้'})")
    lines.append(f"   น้ำหนักการรับฟัง: {res.get('probative_weight')}")
    if res.get('statutory_barrier'):
        lines.append(f"   ข้อจำกัดทางกฎหมาย: {res['statutory_barrier']}")
    else:
        lines.append("   ข้อจำกัดทางกฎหมาย: ไม่มี (ผ่านเกณฑ์การรับฟังตามกฎหมาย)")

    if res.get('exceptions_applied'):
        lines.append("")
        lines.append("   [ข้อยกเว้นที่ปรับใช้]:")
        for ex in res['exceptions_applied']:
            lines.append(f"   • {ex}")

    lines.append("")
    lines.append("   [บทวิเคราะห์ทางนิติศาสตร์]:")
    lines.append(f"   {res.get('analysis')}")

    if res.get('applicable_sections'):
        lines.append("")
        lines.append("   [บทบัญญัติกฎหมายที่ใช้บังคับ]:")
        for sec in res['applicable_sections']:
            lines.append(f"   • {sec}")

    if res.get('precedents'):
        lines.append("")
        lines.append("   [แนวคำพิพากษาศาลฎีกาบรรทัดฐาน]:")
        for prec in res['precedents']:
            lines.append(f"   • {prec}")

    if res.get('recommendations'):
        lines.append("")
        lines.append("   [คำแนะนำทางยุทธศาสตร์คดีความ]:")
        for rec in res['recommendations']:
            lines.append(f"   • {rec}")

    return "\n".join(lines)


def calculate_case_win_probability(
    case_type="civil",
    claimant_tier_a=0,
    claimant_tier_b=0,
    claimant_tier_c=0,
    defense_tier_a=0,
    defense_tier_b=0,
    defense_tier_c=0,
    fatal_loopholes_claimant=0,
    fatal_loopholes_defense=0,
    queen_defense_active=False,
    procedural_defect_claimant=False
):
    """
    Deterministic Mathematical Win Probability Engine (Non-Parametric Math)
    คำนวณโอกาสชนะคดีตามมาตรฐานการพิสูจน์ (Standard of Proof) และน้ำหนักตัวหมากพยาน
    - คดีแพ่ง: Preponderance of the Evidence (ชั่งน้ำหนักน่าเชื่อถือยิ่งกว่า 50.0%)
    - คดีอาญา: Beyond a Reasonable Doubt (ปราศจากข้อสงสัยตามสมควร 85.0%+)
    """
    ct = str(case_type).lower().strip()
    is_criminal = ct in ("criminal", "อาญา", "คดีอาญา")
    
    breakdown_claimant = []
    breakdown_defense = []
    
    if not is_criminal:
        # Civil Standard of Proof
        base_claimant = 50.0
        base_defense = 50.0
        breakdown_claimant.append("ฐานเริ่มต้นคดีแพ่ง (Preponderance Base): 50.0 คะแนน")
        breakdown_defense.append("ฐานเริ่มต้นคดีแพ่ง (Preponderance Base): 50.0 คะแนน")
        
        # Claimant evidence
        pts_c_a = min(40.0, claimant_tier_a * 20.0)
        pts_c_b = min(20.0, claimant_tier_b * 10.0)
        if pts_c_a > 0:
            breakdown_claimant.append(f"พยานเอกสารมหาชน/สเตทเมนต์ (Tier A x {claimant_tier_a}): +{pts_c_a:.1f}")
        if pts_c_b > 0:
            breakdown_claimant.append(f"ภาพแคปแชต/คลิปเสียง (Tier B x {claimant_tier_b}): +{pts_c_b:.1f}")
            
        # Defense evidence
        pts_d_a = min(40.0, defense_tier_a * 20.0)
        pts_d_b = min(20.0, defense_tier_b * 10.0)
        if pts_d_a > 0:
            breakdown_defense.append(f"พยานหลักฐานเด็ดขาดฝ่ายจำเลย (Tier A x {defense_tier_a}): +{pts_d_a:.1f}")
        if pts_d_b > 0:
            breakdown_defense.append(f"พยานหลักฐานฝ่ายจำเลย (Tier B x {defense_tier_b}): +{pts_d_b:.1f}")
            
        # Fatal Loopholes & Procedural Flaws
        penalty_c = (fatal_loopholes_claimant * 30.0) + (25.0 if procedural_defect_claimant else 0.0)
        if fatal_loopholes_claimant > 0:
            breakdown_claimant.append(f"จุดตาย/ช่องโหว่ร้ายแรงโจทก์ (Loopholes x {fatal_loopholes_claimant}): -{fatal_loopholes_claimant * 30.0:.1f}")
        if procedural_defect_claimant:
            breakdown_claimant.append("ข้อบกพร่องทางกระบวนพิจารณาโจทก์ (Procedural Defect): -25.0")
            
        penalty_d = fatal_loopholes_defense * 30.0
        if fatal_loopholes_defense > 0:
            breakdown_defense.append(f"จุดตาย/ช่องโหว่ร้ายแรงจำเลย (Loopholes x {fatal_loopholes_defense}): -{penalty_d:.1f}")
            
        # Queen Defense
        bonus_queen = 30.0 if queen_defense_active else 0.0
        if queen_defense_active:
            breakdown_defense.append("หมากควีน/ข้อยกเว้นกฎหมายเด็ดขาด (Queen Defense): +30.0")
            
        score_c = max(5.0, base_claimant + pts_c_a + pts_c_b - penalty_c)
        score_d = max(5.0, base_defense + pts_d_a + pts_d_b + bonus_queen - penalty_d)
        
        prob_c = round((score_c / (score_c + score_d)) * 100.0, 1)
        prob_d = round(100.0 - prob_c, 1)
        
        prob_c = max(5.0, min(95.0, prob_c))
        prob_d = max(5.0, min(95.0, round(100.0 - prob_c, 1)))
        
        standard_text = "คดีแพ่ง (มาตรฐาน: การชั่งน้ำหนักพยานหลักฐานน่าเชื่อถือยิ่งกว่า 50%+)"
    else:
        # Criminal Standard of Proof (Presumption of Innocence)
        base_prosecution = 35.0
        base_defense = 65.0
        breakdown_claimant.append("ฐานเริ่มต้นคดีอาญา (Presumption of Innocence): 35.0 คะแนน")
        breakdown_defense.append("ฐานเริ่มต้นคดีอาญา (สิทธิสันนิษฐานว่าเป็นผู้บริสุทธิ์): 65.0 คะแนน")
        
        pts_p_a = min(50.0, claimant_tier_a * 25.0)
        pts_p_b = min(20.0, claimant_tier_b * 10.0)
        if pts_p_a > 0:
            breakdown_claimant.append(f"ประจักษ์พยาน/พยานนิติวิทยาศาสตร์ (Tier A x {claimant_tier_a}): +{pts_p_a:.1f}")
        if pts_p_b > 0:
            breakdown_claimant.append(f"พยานแวดล้อมกรณีโจทก์ (Tier B x {claimant_tier_b}): +{pts_p_b:.1f}")
            
        pts_d_a = min(40.0, defense_tier_a * 25.0)
        pts_d_b = min(20.0, defense_tier_b * 10.0)
        if pts_d_a > 0:
            breakdown_defense.append(f"พยานถิ่นที่อยู่/พยานนิติวิทยาศาสตร์จำเลย (Tier A x {defense_tier_a}): +{pts_d_a:.1f}")
        if pts_d_b > 0:
            breakdown_defense.append(f"พยานนำสืบหักล้างจำเลย (Tier B x {defense_tier_b}): +{pts_d_b:.1f}")
            
        penalty_p = (fatal_loopholes_claimant * 35.0) + (30.0 if procedural_defect_claimant else 0.0)
        if fatal_loopholes_claimant > 0:
            breakdown_claimant.append(f"พยานหลักฐานมิชอบ/ข้อสงสัยตามสมควร (ป.วิ.อ. 226/1, 227): -{fatal_loopholes_claimant * 35.0:.1f}")
        if procedural_defect_claimant:
            breakdown_claimant.append("สอบสวนมิชอบ/แจ้งข้อหาไม่มีทนาย (ป.วิ.อ. 134/4): -30.0")
            
        bonus_queen = 35.0 if queen_defense_active else 0.0
        if queen_defense_active:
            breakdown_defense.append("ข้อต่อสู้จำเป็น (ม.67) / เหยื่อค้ามนุษย์ (ม.41) / ขาดเจตนา (ม.59): +35.0")
            
        penalty_d = fatal_loopholes_defense * 35.0
        if fatal_loopholes_defense > 0:
            breakdown_defense.append(f"จำเลยถูกจับกุมพร้อมของกลาง/พิรุธชัดแจ้ง: -{penalty_d:.1f}")
            
        score_p = max(5.0, base_prosecution + pts_p_a + pts_p_b - penalty_p)
        score_d = max(5.0, base_defense + pts_d_a + pts_d_b + bonus_queen - penalty_d)
        
        prob_c = round((score_p / (score_p + score_d)) * 100.0, 1)
        prob_d = round(100.0 - prob_c, 1)
        
        prob_c = max(5.0, min(95.0, prob_c))
        prob_d = max(5.0, min(95.0, round(100.0 - prob_c, 1)))
        
        standard_text = "คดีอาญา (มาตรฐาน: ปราศจากข้อสงสัยตามสมควร Beyond a Reasonable Doubt)"

    silver_bullet = ""
    if prob_c >= 70.0:
        silver_bullet = "พยานหลักฐานฝ่ายรุก/โจทก์ครบองค์ประกอบลูกโซ่ (Chain of Custody) ปิดช่องว่างข้อสงสัย"
    elif prob_d >= 70.0:
        silver_bullet = "ฝ่ายจำเลยมีข้อต่อสู้ตัดตอนกระบวนพิจารณาหรือมีช่องโหว่ร้ายแรงที่ทำให้ยกประโยชน์แห่งความสงสัย"
    else:
        silver_bullet = "คดีอยู่ในภาวะก้ำกึ่ง ผลแพ้ชนะขึ้นอยู่กับดุลพินิจในการขอหมายศาลเรียกพยานบุคคลภายนอกตาม ป.วิ.พ. ม.123"

    return {
        "case_type": ct,
        "standard_of_proof": standard_text,
        "win_probability_claimant": prob_c,
        "win_probability_defense": prob_d,
        "breakdown_claimant": breakdown_claimant,
        "breakdown_defense": breakdown_defense,
        "silver_bullet": silver_bullet
    }


def format_case_probability(res):
    lines = []
    lines.append("[ผลการประเมินโอกาสชนะคดีตามหลักคณิตศาสตร์พยานหลักฐาน (Deterministic Probability Engine)]")
    lines.append(f"   ประเภทคดี: {res['standard_of_proof']}")
    lines.append(f"   🎯 โอกาสชนะฝ่ายรุก/โจทก์ (Offense/Prosecution): {res['win_probability_claimant']}%")
    lines.append(f"   🛡️ โอกาสชนะฝ่ายรับ/จำเลย (Defense): {res['win_probability_defense']}%")
    lines.append("")
    lines.append("   [รายละเอียดการคิดคะแนนพยานหลักฐานฝ่ายรุก]:")
    for b in res['breakdown_claimant']:
        lines.append(f"   • {b}")
    lines.append("")
    lines.append("   [รายละเอียดการคิดคะแนนพยานหลักฐานฝ่ายรับ]:")
    for b in res['breakdown_defense']:
        lines.append(f"   • {b}")
    lines.append("")
    lines.append(f"   ⚡ จุดตายชี้ขาด (The Silver Bullet): {res['silver_bullet']}")
    return "\n".join(lines)


def format_ask_all(query, sections, precedents, glossary):
    out = []
    out.append(f"[ผลการค้นหา]: \"{query}\" (พบเนื้อหาที่เกี่ยวข้อง)")
    out.append("================================================================================")
    out.append("")
    
    out.append(f"[ตัวบทกฎหมาย] ({len(sections)} รายการ)")
    out.append("")
    for s in sections:
        full_sec = get_section(s['section_number'], s['law_code'])
        
        out.append(f"  [{s['law_code']}] มาตรา {s['section_number']} — {s['title']}")
        out.append(f"     ตำแหน่ง: {s['hierarchy_path']}")
        out.append(f"     สถานะ: {'บังคับใช้อยู่' if s['status'] == 'ACTIVE' else 'ยกเลิก'}")
        out.append(f"     ตัวบท: {s['content']}")
        if s['penalty_text']:
            out.append(f"     ผลทางกฎหมาย/โทษ: {s['penalty_text']}")
        if s['compoundable']:
            out.append(f"     [ข้อสังเกต] ยอมความได้: ใช่ — ต้องร้องทุกข์ภายใน 3 เดือน!")
            
        if full_sec and full_sec.get('critical_refs'):
            out.append("")
            out.append(f"     [ข้อยกเว้น/มาตราเชื่อมโยงสำคัญ]:")
            for ref in full_sec['critical_refs']:
                out.append(f"        → [{ref['law_code']}] ม.{ref['section_number']} ({ref['relationship_type']}): {ref['title']}")
        out.append("")
        
    out.append(f"[คำพิพากษาศาลฎีกาบรรทัดฐาน] ({len(precedents)} รายการ)")
    out.append("")
    for p in precedents:
        year_str = f"/{p['year']}" if p.get('year') and '/' not in str(p['dika_number']) else ""
        gc_str = " (ที่ประชุมใหญ่)" if p.get('is_grand_chamber') else ""
        out.append(f"  ฎีกาที่ {p['dika_number']}{year_str}{gc_str}")
        if p.get('summary'):
            out.append(f"     ข้อเท็จจริง: {p['summary']}")
        if p.get('details'):
            out.append(f"     คำวินิจฉัย: {p['details']}")
        if p.get('related_sections'):
            out.append(f"     มาตราที่เกี่ยวข้อง: {p['related_sections']}")
        out.append("")
        
    out.append(f"[คำนิยามทางกฎหมาย] ({len(glossary)} รายการ)")
    out.append("")
    for g in glossary:
        out.append(f"  • {g['term']}: {g['definition']}")
        if g['reference']:
            out.append(f"    แหล่งอ้างอิง: {g['reference']}")
        out.append("")
        
    out.append("================================================================================")
    out.append("[ข้อความปฏิเสธความรับผิดชอบ]: ข้อมูลนี้เป็นเพียงการสืบค้นตัวบทกฎหมาย")
    out.append("เบื้องต้นจากระบบฐานข้อมูล ไม่ใช่คำแนะนำทางกฎหมายของทนายความ")
    out.append("หากมีข้อพิพาท ควรปรึกษาทนายความหรือที่ปรึกษากฎหมายโดยตรง")
    
    return "\n".join(out)

def ask_all(query, limit=5):
    sections = search_sections(query, limit=limit)
    precedents = search_precedents(query, limit=limit)
    glossary = search_glossary(query, limit=limit)
    
    return format_ask_all(query, sections, precedents, glossary)

def safe_parse_json(text):
    if not text:
        return {}
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        import ast
        val = ast.literal_eval(text)
        if isinstance(val, dict):
            return val
    except Exception:
        pass
    try:
        fixed = text.replace("'", '"')
        return json.loads(fixed)
    except Exception:
        pass
    try:
        import re
        # Quote keys: word followed by colon
        fixed = re.sub(r'([{,]\s*)([a-zA-Z_]\w*)\s*:', r'\1"\2":', text)
        # Quote unquoted string values that are dates or non-numbers
        def quote_val(m):
            val = m.group(1).strip()
            if val in ('true', 'false', 'null'):
                return ': ' + val
            try:
                float(val)
                return ': ' + val
            except ValueError:
                if not (val.startswith('"') and val.endswith('"')):
                    return f': "{val}"'
                return ': ' + val
        fixed = re.sub(r':\s*([^,{}]+)', quote_val, fixed)
        return json.loads(fixed)
    except Exception:
        pass
    raise ValueError(f"Cannot parse JSON input: {text}")

def main():
    parser = argparse.ArgumentParser(description="Thai Law RAG Engine — ระบบสืบค้นกฎหมายไทยอัจฉริยะ")
    parser.add_argument("--ask", type=str, help="ค้นหาทุกตารางพร้อมกัน (ตัวบท + ฎีกา + คำนิยาม + Cross-Ref)")
    parser.add_argument("--query", "-q", type=str, help="ค้นหาตัวบทกฎหมาย")
    parser.add_argument("--section", "-s", type=str, help="ดึงมาตราเฉพาะ (เช่น --section 288)")
    parser.add_argument("--law", type=str, default=None, help="กรองตามรหัสกฎหมาย (PENAL, CIVIL, ACT ฯลฯ)")
    parser.add_argument("--precedent", "-p", type=str, help="ค้นหาฎีกาบรรทัดฐาน")
    parser.add_argument("--dika", type=str, help="ดึงฎีกาเฉพาะเรื่อง (เช่น --dika 1856/2538)")
    parser.add_argument("--glossary", "-g", type=str, nargs="?", const="all", help="ค้นหาคำนิยามทางกฎหมาย")
    parser.add_argument("--cross-ref", "-x", type=str, help="แสดง Cross-References ของมาตรา")
    parser.add_argument("--fetch-official", type=str, nargs="+", help="ดึงคำพิพากษาศาลฎีกาฉบับทางการโดยตรงจาก deka.supremecourt.or.th (เช่น --fetch-official 8477 2563 หรือ --fetch-official 8477/2563)")
    parser.add_argument("--force-refresh", action="store_true", help="บังคับดึงข้อมูลใหม่จากศาลโดยไม่ใช้แคชในเครื่อง")
    parser.add_argument("--limit", "-l", type=int, default=5, help="จำกัดผลลัพธ์ (default: 5)")
    parser.add_argument("--json", action="store_true", help="ผลลัพธ์เป็น JSON")
    
    # 5 Specialized Legal Engines Arguments
    parser.add_argument("--inheritance", type=str, help="คำนวณมรดก (รับ JSON เช่น '{\"estate\": 1200000, \"spouse\": true, \"children\": 2}')")
    parser.add_argument("--limitations", type=str, help="คำนวณอายุความ (รับ JSON เช่น '{\"case_type\": \"criminal\", \"penalty_years\": 5, \"is_compoundable\": true}')")
    parser.add_argument("--severance", type=str, help="คำนวณค่าชดเชยเลิกจ้าง (รับ JSON เช่น '{\"tenure_months\": 24, \"monthly_wage\": 30000}')")
    parser.add_argument("--interest", type=str, help="คำนวณดอกเบี้ยผิดนัด (รับ JSON เช่น '{\"principal\": 100000, \"start_date\": \"2022-01-01\", \"end_date\": \"2024-01-01\"}')")
    parser.add_argument("--evidence", type=str, help="ตรวจสอบความสามารถในการรับฟังพยานหลักฐาน (รับ JSON เช่น '{\"dispute_type\": \"loan\", \"amount\": 50000, \"evidence_type\": \"electronic_chat\"}')")
    parser.add_argument("--probability", type=str, help="คำนวณโอกาสชนะคดีตามหลักคณิตศาสตร์พยานหลักฐาน (รับ JSON เช่น '{\"case_type\": \"civil\", \"claimant_tier_a\": 1, \"defense_tier_b\": 1}')")
    
    args = parser.parse_args()
    
    if not any([args.ask, args.query, args.section, args.precedent, args.dika, args.fetch_official, args.glossary, args.cross_ref,
                args.inheritance, args.limitations, args.severance, args.interest, args.evidence, args.probability]):
        parser.print_help()
        sys.exit(0)
        
    try:
        # Calculator 1: Inheritance
        if args.inheritance:
            params = safe_parse_json(args.inheritance)
            res = calculate_thai_inheritance(
                estate_value=params.get("estate", params.get("estate_value", 0)),
                has_spouse=params.get("spouse", params.get("has_spouse", False)),
                num_children=params.get("children", params.get("num_children", 0)),
                num_parents=params.get("parents", params.get("num_parents", 0)),
                num_full_siblings=params.get("full_siblings", params.get("num_full_siblings", 0)),
                num_half_siblings=params.get("half_siblings", params.get("num_half_siblings", 0)),
                num_grandparents=params.get("grandparents", params.get("num_grandparents", 0)),
                num_uncles_aunts=params.get("uncles_aunts", params.get("num_uncles_aunts", 0))
            )
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                print(f"[ผลการคำนวณการแบ่งทรัพย์มรดก]")
                print(f"   กองมรดกทั้งหมด: {res['estate_value']:,.2f} บาท")
                print(f"   คำอธิบาย: {res['explanation']}")
                print("\n   สัดส่วนการแบ่ง:")
                for k, v in res['shares'].items():
                    per_head_str = f" (คนละ {v['per_head']:,.2f} บาท)" if 'per_head' in v else ""
                    print(f"   • {k}: {v['amount']:,.2f} บาท ({v['percent']}%) {per_head_str}")
                print(f"\n   มาตรากฎหมายที่ใช้บังคับ: {', '.join(res['citations'])}")

        # Calculator 2: Statute of Limitations
        elif args.limitations:
            params = safe_parse_json(args.limitations)
            res = calculate_statute_of_limitations(
                case_type=params.get("case_type", params.get("type", "criminal")),
                penalty_years=params.get("penalty_years", params.get("penalty", 0)),
                is_compoundable=params.get("is_compoundable", params.get("compoundable", False)),
                claim_type=params.get("claim_type", None)
            )
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                print(f"[ผลการคำนวณอายุความ]")
                print(f"   ประเภทคดี: {res['case_type']}")
                if res['limitation_years'] > 0:
                    print(f"   อายุความฟ้องร้อง: {res['limitation_years']} ปี")
                if res['limitation_months'] > 0:
                    print(f"   อายุความร้องทุกข์: {res['limitation_months']} เดือน")
                if res['critical_warning']:
                    print(f"\n   {res['critical_warning']}")
                print(f"\n   มาตรากฎหมายที่ใช้บังคับ: {', '.join(res['citations'])}")

        # Calculator 3: Severance Pay
        elif args.severance:
            params = safe_parse_json(args.severance)
            res = calculate_severance_pay(
                tenure_months=params.get("tenure_months", params.get("months", 0)),
                monthly_wage=params.get("monthly_wage", params.get("wage", 0)),
                termination_reason=params.get("termination_reason", params.get("reason", "general"))
            )
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                print(f"[ผลการคำนวณค่าชดเชยการเลิกจ้าง]")
                print(f"   อายุงาน: {res['tenure_months']:.1f} เดือน, ค่าจ้างเดือนละ: {res['monthly_wage']:,.2f} บาท")
                print(f"   สิทธิได้รับค่าชดเชย: {res['severance_days']} วัน = {res['severance_amount']:,.2f} บาท")
                if res.get('advance_notice_pay', 0) > 0:
                    print(f"   สินจ้างแทนการบอกกล่าวล่วงหน้า (ค่าตกใจ): {res['advance_notice_pay']:,.2f} บาท")
                    print(f"   รวมเงินที่ควรได้รับเบื้องต้น: {res['total_estimated']:,.2f} บาท")
                print(f"   คำอธิบาย: {res['explanation']}")
                print(f"\n   มาตรากฎหมายที่ใช้บังคับ: {', '.join(res['citations'])}")

        # Calculator 4: Legal Interest
        elif args.interest:
            params = safe_parse_json(args.interest)
            res = calculate_legal_interest(
                principal=params.get("principal", 0),
                start_date_str=params.get("start_date", ""),
                end_date_str=params.get("end_date", None),
                custom_rate=params.get("custom_rate", params.get("rate", None)),
                interest_type=params.get("interest_type", "default")
            )
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                print(f"[ผลการคำนวณดอกเบี้ยผิดนัด / หนี้เงิน]")
                print(f"   เงินต้น: {res['principal']:,.2f} บาท")
                print(f"   ระยะเวลา: {res.get('start_date')} ถึง {res.get('end_date')} (รวม {res.get('total_days')} วัน)")
                if res.get("breakdown"):
                    print("\n   รายละเอียดการคำนวณตามช่วงเวลา:")
                    for b in res["breakdown"]:
                        print(f"   • ช่วง {b['period']}: {b['days']} วัน @ ร้อยละ {b['rate_percent']}% ต่อปี = {b['interest']:,.2f} บาท")
                print(f"\n   ดอกเบี้ยรวม: {res.get('total_interest', 0.0):,.2f} บาท")
                print(f"   ยอดหนี้รวมทั้งสิ้น: {res.get('total_debt', 0.0):,.2f} บาท")
                if res.get("warning"):
                    print(f"\n   {res['warning']}")
                print(f"\n   มาตรากฎหมายที่ใช้บังคับ: {', '.join(res['citations'])}")

        # Calculator 5: Evidence Admissibility Engine
        elif args.evidence:
            params = safe_parse_json(args.evidence)
            res = check_evidence_admissibility(
                dispute_type=params.get("dispute_type", params.get("case_type", "loan")),
                amount=params.get("amount", 0.0),
                evidence_type=params.get("evidence_type", "paper_signed"),
                has_written_evidence=params.get("has_written_evidence", False),
                has_signature=params.get("has_signature", False),
                is_electronic=params.get("is_electronic", False),
                electronic_details=params.get("electronic_details", None),
                exceptions_claimed=params.get("exceptions_claimed", None)
            )
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                print(format_evidence_admissibility(res))

        # Mathematical Win Probability Engine (Non-Parametric Math)
        elif args.probability:
            params = safe_parse_json(args.probability)
            res = calculate_case_win_probability(
                case_type=params.get("case_type", "civil"),
                claimant_tier_a=params.get("claimant_tier_a", 0),
                claimant_tier_b=params.get("claimant_tier_b", 0),
                claimant_tier_c=params.get("claimant_tier_c", 0),
                defense_tier_a=params.get("defense_tier_a", 0),
                defense_tier_b=params.get("defense_tier_b", 0),
                defense_tier_c=params.get("defense_tier_c", 0),
                fatal_loopholes_claimant=params.get("fatal_loopholes_claimant", 0),
                fatal_loopholes_defense=params.get("fatal_loopholes_defense", 0),
                queen_defense_active=params.get("queen_defense_active", False),
                procedural_defect_claimant=params.get("procedural_defect_claimant", False)
            )
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                print(format_case_probability(res))

        elif args.ask:
            result = ask_all(args.ask, limit=args.limit)
            if args.json:
                print(json.dumps({"result": result}, ensure_ascii=False, indent=2))
            else:
                print(result)
                
        elif args.query:
            results = search_sections(args.query, limit=args.limit, law_code=args.law)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for r in results:
                    print(f"[{r['law_code']} ม.{r['section_number']}] {r['title']}\n{r['content']}\n")
                    
        elif args.section:
            result = get_section(args.section, law_code=args.law)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif result:
                print(f"[{result['law_code']} ม.{result['section_number']}] {result['title']}")
                print(f"สถานะ: {result['status']}")
                print(f"{result['content']}")
                if result['compoundable']:
                    print(f"[ข้อสังเกต] ยอมความได้: ใช่ — ต้องร้องทุกข์ภายใน 3 เดือน!")
                if result['critical_refs']:
                    print("\n[ข้อยกเว้น/มาตราเชื่อมโยงสำคัญ]:")
                    for ref in result['critical_refs']:
                        print(f"  -> [{ref['law_code']}] ม.{ref['section_number']} ({ref['relationship_type']})")
            else:
                print("ไม่พบข้อมูลมาตรานี้")
                
        elif args.cross_ref:
            results = get_cross_refs(args.cross_ref, law_code=args.law)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for r in results:
                    print(f"-> [{r['law_code']}] ม.{r['section_number']} [{r['relationship_type']}] (Critical: {r['is_critical']})")
                    
        elif args.precedent:
            results = search_precedents(args.precedent, limit=args.limit)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for r in results:
                    year_str = f"/{r['year']}" if r.get('year') and '/' not in str(r['dika_number']) else ""
                    gc_str = " (ที่ประชุมใหญ่)" if r.get('is_grand_chamber') else ""
                    print(f"ฎีกาที่ {r['dika_number']}{year_str}{gc_str}")
                    print(f"   ข้อเท็จจริง: {r['summary']}")
                    print(f"   คำวินิจฉัย: {r['details']}")
                    print(f"   มาตราที่เกี่ยวข้อง: {r['related_sections']}\n")
                    
        elif args.dika:
            result = get_precedent(args.dika)
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif result:
                year_str = f"/{result['year']}" if result.get('year') and '/' not in str(result['dika_number']) else ""
                gc_str = " (ที่ประชุมใหญ่)" if result.get('is_grand_chamber') else ""
                print(f"ฎีกาที่ {result['dika_number']}{year_str}{gc_str}")
                print(f"ข้อเท็จจริง: {result['summary']}")
                print(f"คำวินิจฉัย: {result['details']}")
                if result.get('related_sections'):
                    print(f"มาตราที่เกี่ยวข้อง: {result['related_sections']}")
            else:
                print("ไม่พบข้อมูลฎีกานี้")

        elif args.fetch_official:
            if len(args.fetch_official) == 1:
                val = args.fetch_official[0]
                if "/" in val:
                    dika_no, year = val.split("/", 1)
                else:
                    print("กรุณาระบุปี พ.ศ. เช่น --fetch-official 8477 2563 หรือ --fetch-official 8477/2563")
                    sys.exit(1)
            else:
                dika_no, year = args.fetch_official[0], args.fetch_official[1]
                
            res = fetch_official_dika(dika_no, year, force_refresh=args.force_refresh)
            if args.json:
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                if not res["success"]:
                    print(f"[ไม่พบข้อมูล] ฎีกาที่ {res['dika_number']} ในระบบฐานข้อมูลศาลฎีกา (deka.supremecourt.or.th)")
                    if res.get("error"):
                        print(f"   สาเหตุ: {res['error']}")
                else:
                    if res.get("from_cache"):
                        print(f"[Local Cache Hit] โหลดจากฐานข้อมูลท้องถิ่นสำเร็จใน <1ms (Offline / 0 Network Packets)")
                    else:
                        print(f"[Court Portal Ingested] ดึงจากศาลฎีกาสำเร็จและแคชลงฐานข้อมูลแล้ว")
                    print(f"[{res['title']}] — สำนักงานศาลยุติธรรม (Official Court Record)")
                    print(f"แหล่งที่มา: {res['source_url']}")
                    print("=" * 60)
                    if res.get("summary"):
                        print("[ย่อสั้น / ข้อเท็จจริงและหลักกฎหมาย]:")
                        print(f"   {res['summary']}")
                        print("-" * 60)
                    if res.get("full_text"):
                        print("[ย่อยาว / คำวินิจฉัยศาลฎีกาฉบับเต็ม]:")
                        print(f"   {res['full_text']}")
                
        elif args.glossary:
            if args.glossary == "all":
                results = search_glossary("", limit=100)
            else:
                results = search_glossary(args.glossary, limit=args.limit)
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                for r in results:
                    ref_str = f" (อ้างอิง: {r['reference']})" if r.get('reference') else ""
                    print(f"• {r['term']}: {r['definition']}{ref_str}")
                        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
