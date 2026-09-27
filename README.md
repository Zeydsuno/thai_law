# Thai Law RAG Engine (ระบบปัญญาประดิษฐ์สืบค้นและวินิจฉัยกฎหมายไทยแบบไร้ภาพหลอน)

ระบบ **Thai Legal RAG (Retrieval-Augmented Generation)** แบบ Local-First & Zero-Hallucination ความเร็วสูงระดับเสี้ยววินาที (< 2ms) ขับเคลื่อนด้วย **SQLite FTS5 (BM25) + Typed Cross-Reference Knowledge Graph** พร้อม **5 กลไกการคำนวณและวินิจฉัยทางนิติศาสตร์แบบดีเทอร์มินิสติก (Deterministic Legal Engines)** และการตรวจสอบความสมบูรณ์ระดับไบต์ด้วยรหัสลับ SHA-256 เทียบเคียงตัวบทจริงจากสำนักงานคณะกรรมการกฤษฎีกา 100%

> [!IMPORTANT]
> **ใบอนุญาตใช้งานและการคุ้มครองทรัพย์สินทางปัญญา (Intellectual Property & Noncommercial Notice):**  
> ซอฟต์แวร์ สถาปัตยกรรม และงานวิจัยนี้ เผยแพร่ภายใต้สัญญาอนุญาต **PolyForm Noncommercial License 1.0.0** เพื่อวัตถุประสงค์ในการศึกษา การวิจัยทางวิชาการ (Academic Research) และการตรวจสอบสถาปัตยกรรม (Peer Review) เท่านั้น  
> 🚫 **ไม่อนุญาตให้นำไปใช้ในเชิงพาณิชย์ แสวงหากำไร นำไปรันในสภาพแวดล้อม Production หรือเปิดบริการ API แข่งขันโดยไม่ได้รับอนุญาต**  
> 🔒 **การคุ้มครองข้อมูลและเอกสารงานวิจัย (Data & Paper Protection):** เพื่อป้องกันการละเมิดทรัพย์สินทางปัญญาและการคัดลอกผลงานโดยมิได้รับอนุญาต เอกสารงานวิจัยฉบับสมบูรณ์และฐานข้อมูลคลังกฎหมายตัวเต็ม (`thai_law.db`) ได้รับการจัดเก็บเป็นทรัพย์สินส่วนบุคคล (Private Assets) และไม่ได้รวมอยู่ใน Public Git  
> 💼 หากต้องการสิทธิ์เข้าถึงฐานข้อมูลคลังกฎหมายฉบับสมบูรณ์ (142 มาตรา / 1,049 ฎีกา), เอกสารงานวิจัยฉบับสมบูรณ์สำหรับ Peer Review หรือสิทธิ์ใช้งานเชิงพาณิชย์ (Commercial / Enterprise License) โปรดติดต่อผู้พัฒนาโดยตรง: **Attidmese Bunsua (นายอัตติรมีซี บุญเสือ / Zeydsuno)**

สถาปัตยกรรมนี้ได้รับการออกแบบและพัฒนาขึ้นเพื่อแก้ไข 4 ข้อจำกัดสำคัญของแบบทดสอบมาตรฐาน **NitiBench (arXiv:2502.10868 โดย VISAI & VISTEC)**:
1. **แก้ Context Bloat ของ NitiLink:** ใช้ **Typed Cross-Reference Graph** กรองเฉพาะข้อยกเว้น (`EXCEPTION`), เหตุฉกรรจ์/เพิ่มโทษ (`AGGRAVATION`), มาตราเชื่อมโยง (`REFERRED`) และบทนิยาม (`DEFINITION`) ที่เป็นจุดชี้ขาดทางคดีเท่านั้น
2. **แก้ Nested Structure:** เชื่อมโยงมาตราความผิดและมาตราโทษผ่าน Relational Foreign Key ข้ามประมวลกฎหมาย ทำให้สืบค้นผลทางกฎหมายได้ครบถ้วนแม้บทบัญญัติจะอยู่ต่างหมวดหรือต่างประมวล
3. **แก้ Missable Details:** ใช้ **Hybrid Search (SQLite FTS5 + LIKE Fallback + Semantic Intent Mapping)** ลดจุดอ่อนของการสืบค้นแบบเวกเตอร์ (Vector Search) ที่มักแยกคำเฉพาะทางกฎหมายไม่ออก
4. **แก้ Hidden Hierarchical Information:** ทุกระเบียนระบุ `hierarchy_path` (เช่น `ป.พ.พ. > บรรพ 3 > ลักษณะ 9 > หมวด 2 > มาตรา 653`) ป้องกันความสับสนระหว่างมาตราที่มีคำคล้ายกันแต่อยู่คนละหมวด

---

## สรุปฐานข้อมูลคลังกฎหมาย (Database Summary)

### ตารางเปรียบเทียบชุดข้อมูล (Public Demo Sandbox vs Full Production Corpus)

| คุณสมบัติ | Public Demo Sandbox (ติดมากับ Git รันได้ทันที) | Full Production Corpus (Private / ขอรับสิทธิ์) |
| :--- | :--- | :--- |
| **ไฟล์ฐานข้อมูล** | `data/thai_law_demo.db` (252 KB) | `data/thai_law.db` (5.0 MB) |
| **ตัวบทกฎหมายรับรอง** | **32 มาตราแกนหลัก** (ป.อ. 288, 334, 341, ป.พ.พ. 650, 653, 1629 ฯลฯ) | **142 มาตราฉบับเต็ม** (ครอบคลุมทุกประมวลและ พ.ร.บ.เฉพาะ) |
| **คำพิพากษาศาลฎีกา** | **ฎีกาบรรทัดฐานสำคัญ** (Landmarks เช่น 8477/2563, 4101/2562 ฯลฯ) | **1,052 คำพิพากษา** ยืนยันตรงกับระบบศาลฎีกา |
| **5 Deterministic Engines** | ✅ **ทำงานได้เต็ม 100%** (มรดก, อายุความ, ค่าชดเชย, ดอกเบี้ย, พยาน ม.94) | ✅ **ทำงานได้เต็ม 100%** |
| **การสืบค้น (RAG Latency)** | ความเร็วสูงระดับเสี้ยววินาที (< 2ms) | ความเร็วสูงระดับเสี้ยววินาที (< 2ms) |
| **การทดสอบและประเมินผล** | โคลนไปแล้วสั่งรัน CLI ทดสอบฟังก์ชันได้ทันทีโดยไม่ต้องตั้งค่า | ชุดทดสอบวิศวกรรมมาตรฐาน 108/108 เคส (Pass 100%) |
| **สัญญาอนุญาต** | PolyForm Noncommercial 1.0.0 (ฟรีเพื่อการศึกษา/ทดสอบ) | Commercial / Enterprise License |

---

## โครงสร้างโปรเจกต์ (Project Structure)

```
thai_law/
├── data/
│   ├── thai_law_demo.db      # ฐานข้อมูลตัวอย่างสาธารณะ (32 มาตรา / รันได้ทันทีไม่ต้องขอสิทธิ์)
│   ├── corpus_sections.json  # สรุปโครงสร้างคลังตัวบทในรูปแบบ JSON
│   └── thai_law.db           # [Private Asset] ฐานข้อมูลฉบับสมบูรณ์ (142 มาตรา / 1,052 ฎีกา)
├── raw_sources/              # ไฟล์ตัวบทกฎหมายต้นฉบับกฤษฎีกาแยกตามหมวดหมู่ (142 ไฟล์)
│   └── manifest.json         # บัญชีคุมรหัสลับ SHA-256 ระดับไบต์
├── compile_demo_db.py        # ตัวสร้างฐานข้อมูล Demo Sandbox สำหรับสาธารณะ
├── compile_corpus.py         # ตัวคอมไพล์ฐานข้อมูลฉบับเต็มและ Seed ข้อมูล
├── harvester.py              # เครื่องมือสกัดตัวบทดิบและคำนวณแฮช SHA-256 บันทึกลง raw_sources
├── verify_integrity.py       # เครื่องมือ Audit ตรวจสอบความถูกต้องระดับไบต์ (Cryptographic Parity)
├── rag_engine.py             # กลไกสืบค้น RAG Engine, กราฟความรู้, และ 5 เครื่องมือวินิจฉัย
├── test_suite_audit.py       # ชุดทดสอบอัตโนมัติ 4 มิติ (Base, Boundary, Edge, Corner รวม 108 เคส)
├── ingest_tscc.py            # ตัวนำเข้าคลังคำพิพากษาศาลฎีกาจาก TSCC Dataset
├── AUDIT_REPORT.md           # รายงานผลการ Audit คุณภาพระบบ 4 มิติ
├── DECISION.md               # บันทึกการตัดสินใจเชิงสถาปัตยกรรม (Architecture Decision Records - ADR 7 ข้อ)
├── CITATION.cff              # บัญชีกำหนดการอ้างอิงทางวิชาการมาตรฐานสากล (GitHub Native Citation)
├── LICENSE                   # สัญญาอนุญาตซอฟต์แวร์แบบ PolyForm Noncommercial 1.0.0
└── README.md                 # คู่มือการใช้งานระบบ
```

---

## การติดตั้งและการเริ่มใช้งาน (Quick Start)

ระบบถูกออกแบบภายใต้ปรัชญา Pure Python Standard Library **ไม่ต้องติดตั้ง Third-Party Library ใดๆ (Zero Pip Dependencies)**

### 1. โคลนคลังโค้ด
```bash
git clone https://github.com/Zeydsuno/thai_law.git
cd thai_law
```

### 2. ตรวจสอบความสมบูรณ์เชิงรหัสลับ (Cryptographic Parity Audit)
```bash
python verify_integrity.py --all
```

### 3. รันชุดทดสอบมาตรฐานวิศวกรรม 4 มิติ (103 Test Cases)
```bash
python test_suite_audit.py
```

---

## กลไกการคำนวณและวินิจฉัยทางนิติศาสตร์ 5 ระบบ (5 Deterministic Engines)

### 1. ระบบตรวจสอบความสามารถในการรับฟังพยานหลักฐาน (Evidence Admissibility Engine)
วินิจฉัยกฎการรับฟังพยานหลักฐานตาม ป.วิ.พ. ม.94 (Parol Evidence Rule), สัญญากู้ยืมเงินเกิน 2,000 บาท ตาม ป.พ.พ. ม.653, ความสมบูรณ์ของหลักฐานดิจิทัลตาม พ.ร.บ.ว่าด้วยธุรกรรมทางอิเล็กทรอนิกส์ พ.ศ. 2544 (ม.7 ถึง 12), ข้อยกเว้นการสืบพยานบุคคลหักล้างเอกสารตาม ม.94 วรรคท้าย (นิติกรรมอำพราง, ความไม่สมบูรณ์แห่งมูลหนี้/ไม่ได้รับเงินกู้จริงตามฎีกา 8477/2563 และ 4101/2562, เหตุสุดวิสัยเอกสารสูญหาย ม.93(2)), และข้อเตือนการปิดอากรแสตมป์ตาม ป.รัษฎากร ม.118

```bash
# ตัวอย่าง: กู้ยืมเงิน 100,000 บาท ผ่านแชต LINE มีสลิปโอนเงิน
python rag_engine.py --evidence '{"dispute_type": "loan", "amount": 100000, "has_written_contract": false, "electronic_evidence": ["line_chat", "bank_transfer_slip"]}'

# ตัวอย่าง: กู้ยืมเงินมีสัญญาเป็นหนังสือ แต่ต่อสู้ว่าไม่ได้รับเงินกู้จริง (ม.94 วรรคท้าย)
python rag_engine.py --evidence '{"dispute_type": "loan", "amount": 200000, "has_written_contract": true, "exceptions_claimed": ["no_consideration"]}'
```

### 2. เครื่องคำนวณแบ่งทรัพย์มรดก (ป.พ.พ. ม.1599, 1629, 1630, 1635)
คำนวณสัดส่วนทายาทโดยธรรม 6 ลำดับและคู่สมรสตามหลักญาติสนิทตัดญาติห่าง บิดามารดารับส่วนแบ่งเสมือนชั้นบุตร และสัดส่วนคู่สมรสตาม ม.1635

```bash
python rag_engine.py --inheritance '{"estate": 1200000, "spouse": true, "children": 2, "parents": 1}'
```

### 3. เครื่องคำนวณอายุความ (ป.อ. ม.95, 96 / ป.พ.พ. ม.193/30, 448)
คำนวณอายุความฟ้องร้อง พร้อมระบบเตือนเงื่อนไขคดียอมความได้ที่ต้องร้องทุกข์ภายใน 3 เดือนตาม ป.อ. ม.96

```bash
# คดีอาญา (เตือนอายุความร้องทุกข์ 3 เดือนในคดียอมความได้)
python rag_engine.py --limitations '{"case_type": "criminal", "penalty_years": 3, "is_compoundable": true}'

# คดีแพ่ง (ละเมิด 1 ปี, สัญญากู้ยืม 10 ปี, สิทธิเรียกร้องค่าจ้างแรงงาน 2 ปี)
python rag_engine.py --limitations '{"case_type": "civil", "claim_type": "tort"}'
```

### 4. เครื่องคำนวณค่าชดเชยการเลิกจ้าง (พ.ร.บ. คุ้มครองแรงงาน ม.118, 119)
คำนวณอัตราค่าชดเชยตามอายุงาน 6 ระดับ (30 ถึง 400 วัน) พร้อมสินจ้างแทนการบอกกล่าวล่วงหน้า (ค่าตกใจ) และตรวจจับข้อยกเว้นการเลิกจ้างตาม ม.119

```bash
python rag_engine.py --severance '{"tenure_months": 36, "monthly_wage": 45000}'
```

### 5. เครื่องคำนวณดอกเบี้ยผิดนัดและหนี้เงิน (ป.พ.พ. ม.224 & ม.654)
คำนวณดอกเบี้ยผิดนัดอัตราใหม่ 5% ต่อปี (แก้ไขเมื่อ 11 เม.ย. 2564) โดยระบบแยกคำนวณ 2 ช่วงเวลาอัตโนมัติ (ช่วงก่อนหน้า 7.5% และช่วงหลัง 5.0%) พร้อมตรวจจับข้อตกลงดอกเบี้ยเงินกู้เกิน 15% ที่ตกเป็นโมฆะทั้งหมดตาม ม.654

```bash
# ดอกเบี้ยผิดนัดช่วงคาบเกี่ยวกฎหมายใหม่ 11 เม.ย. 2564
python rag_engine.py --interest '{"principal": 100000, "start_date": "2020-01-01", "end_date": "2022-01-01"}'

# ตรวจสอบเงินกู้ดอกเบี้ยเกินอัตรา (โมฆะเฉพาะส่วนดอกเบี้ย)
python rag_engine.py --interest '{"principal": 50000, "start_date": "2023-01-01", "end_date": "2023-07-01", "rate": 20, "interest_type": "loan"}'
```

---

## การสืบค้นตัวบทกฎหมายและฎีกาผ่าน CLI (CLI Query Guide)

### 1. สืบค้นแบบรวมทุกตาราง (Omnibus Search)
สืบค้นด้วยภาษาชาวบ้าน แปลงเป็นศัพท์เทคนิคทางกฎหมาย พร้อมดึงตัวบท ฎีกา คำนิยาม และคำเตือนขาดอายุความโดยอัตโนมัติ

```bash
python rag_engine.py --ask "บัญชีม้า โดนหลอกเปิดบัญชี"
python rag_engine.py --ask "ยืมเงินผ่านแชตไลน์ ดอกเบี้ยเกิน"
python rag_engine.py --ask "ทวงหนี้ประจานบนเฟซบุ๊ก"
python rag_engine.py --ask "ตีความสัญญาสำเร็จรูป"
python rag_engine.py --ask "หมายเรียกภาษี"
```

### 2. ดึงข้อมูลมาตราเฉพาะ (พร้อมขยาย Cross-References ข้อยกเว้นอัตโนมัติ)
```bash
python rag_engine.py --section 288
python rag_engine.py --section 653 --law CIVIL
python rag_engine.py --section 19 --law REVENUE
python rag_engine.py --section 6 --law ACT
```

### 3. สืบค้นคำพิพากษาศาลฎีกาบรรทัดฐาน
```bash
python rag_engine.py --precedent "บัญชีม้า"
python rag_engine.py --precedent "ตัวการไม่เปิดเผยชื่อ"
python rag_engine.py --dika "8477/2563"
```

### 4. ตรวจสอบเส้นใยความสัมพันธ์ของมาตรา (Cross-References)
```bash
python rag_engine.py --cross-ref 653 --law CIVIL
python rag_engine.py --cross-ref 4 --law ACT
python rag_engine.py --cross-ref 50 --law REVENUE
```

### 5. ดึงคำพิพากษาฉบับทางการจากระบบศาลฎีกา (Tier 3 Fetch)
```bash
python rag_engine.py --fetch-official 8477 2563
```

---

## เอกสารอ้างอิงและงานวิจัย (Research Citation)

รายละเอียดการตัดสินใจเชิงสถาปัตยกรรม (ADR) บันทึกไว้ใน [DECISION.md](DECISION.md)  
เอกสารงานวิจัยฉบับสมบูรณ์ (Full Academic Paper - 5 บท) พร้อมผลการประเมิน NitiBench และการพิสูจน์ทางคณิตศาสตร์ จัดเก็บเป็นความลับทางวิชาการ สามารถติดต่อขอรับเพื่อการตรวจสอบ (Peer Review) หรือวิจัยต่อยอดได้โดยตรงจากผู้ประพันธ์

### รูปแบบการอ้างอิง (BibTeX)
หากคุณนำผลงานวิจัย สถาปัตยกรรม หรือโครงสร้างชุดข้อมูลนี้ไปใช้อ้างอิงทางวิชาการ โปรดอ้างอิงตามรูปแบบดังต่อไปนี้:

```bibtex
@misc{bunsua2026thailaw,
  author       = {Bunsua, Attidmese},
  title        = {Thai Law RAG Engine: Zero-Hallucination Legal AI Architecture with Cryptographic Verification and Hybrid Symbolic Engines},
  year         = {2026},
  publisher    = {GitHub},
  journal      = {GitHub repository},
  howpublished = {\url{https://github.com/Zeydsuno/thai_law}}
}
```

**ผู้วิจัยและผู้ถือลิขสิทธิ์:** นายอัตติรมีซี บุญเสือ (Attidmese Bunsua / Zeydsuno)  
**โครงการ:** Thai Law Scholar & Legal Adversary Engine (2568-2569)  
**สัญญาอนุญาต:** [PolyForm Noncommercial License 1.0.0](LICENSE) (สงวนลิขสิทธิ์สำหรับการใช้งานเชิงพาณิชย์)  

---

## สิทธิการใช้งานเชิงพาณิชย์ (Commercial & Enterprise Licensing)

ซอฟต์แวร์นี้เปิดให้ตรวจสอบซอร์สโค้ดและใช้งานเพื่อการศึกษา/วิจัยโดยไม่คิดมูลค่า แต่**ไม่อนุญาตให้นำไปใช้ในเชิงพาณิชย์ หรือติดตั้งเป็นแกนหลักในระบบ Production ขององค์กรโดยไม่ได้รับอนุญาต**

หากคุณเป็นบริษัท สตาร์ทอัพ สำนักงานกฎหมาย หรือหน่วยงานที่ต้องการ:
1. สิทธิ์การใช้งานเชิงพาณิชย์ (Commercial License)
2. สิทธิ์เข้าถึงฐานข้อมูลคลังตัวบทและฎีกาฉบับสมบูรณ์ (Full Production Corpus Database)
3. บริการติดตั้งและเชื่อมต่อระบบเข้ากับระบบงานภายใน (Enterprise Integration & Support)

กรุณาติดต่อผู้พัฒนา: **Attidmese Bunsua (นายอัตติรมีซี บุญเสือ)** ผ่านช่องทาง GitHub Issue หรือช่องทางติดต่อส่วนตัวของผู้พัฒนา
