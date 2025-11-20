#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DLAS Fast HTML Converter  v2.3.2  (Auto 3SHAPE / EXO + ZIP)
----------------------------------------------------------------
· 2025‑09‑02

◼ (중요) 치식 인식 강화 + 우선순위 조정
   - 치식 정규식 보강: 날짜/수량 같은 숫자를 완전히 배제하고 FDI(11–48)만 추출
   - 파일명에서 확실한 치식을 찾으면 modelInfo의 Jaw 추정보다 *치식 우선*
     → '31-41-42-modelbase'가 Lower Scan으로 정확 분류

◼ (v2.1.6 유지) modelInfo 기반으로 모델/베이스/gingiva/marker/scan 계열의 상·하악을
   우선 추정하되, 이번 버전부터 *치식이 있으면 치식이 최우선*.

◼ (핵심 버그픽스 v2.1.5 계승) modelInfo + constructionInfo 동시 존재 시,
   파일 ‘소유자(owner)’ 기준 단일 변환만 적용하여 변환 중복 방지.
   · owner == 'both'일 때 모델/베이스/gingiva는 modelInfo 우선,
     그 외(크라운/어버트먼트/스캔바디)는 constructionInfo 우선.

  ◼ EXO: occlusion*.stl은 'etc'로 분류, 상/하 스캔·크라운 교차로 BITE 자동 생성
  ◼ Auto 모드: *.3ox → 3SHAPE, *.constructionInfo/*.modelInfo → EXO
  ◼ EXO 모드: constructionInfo/modelInfo 파싱 + 좌표 변환 적용(이름 보존)
  ◼ ZIP 자동 처리: 폴더 안의 .zip을 temp에 풀어 EXO/3SHAPE 패키지 인식
----------------------------------------------------------------
"""

# ----------------------------------------------------------------------
# 표준 라이브러리
# ----------------------------------------------------------------------
import os
import re
import sys
import time
import json
import base64
import threading
import multiprocessing
import shutil
import tempfile
import zipfile
import subprocess
from string import Template
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Optional

# ----------------------------------------------------------------------
# 외부 라이브러리
# ----------------------------------------------------------------------
import pandas as pd
import vtk
import trimesh
from PySide6.QtCore import Qt, QTimer, QMetaObject, Q_ARG, QSettings, Signal, QSize
from PySide6.QtGui  import QFont, QPixmap, QIcon, QCursor, QMovie
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox, QMessageBox,
    QCheckBox, QProgressBar, QTextEdit, QDialog, QTableWidget,
    QTableWidgetItem, QFrame, QScrollArea
)

try:
    from modules.common_styles import Style
except ImportError:
    from common_styles import Style

# ==============================================================================
# utils – resource_path
# ==============================================================================
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".dlas_html_converter.json")

def resource_path(relative_path: str) -> str:
    script_dir = Path(__file__).resolve().parent
    meipass    = Path(getattr(sys, "_MEIPASS", ""))  # PyInstaller일 때
    candidates = [
        script_dir / relative_path,
        script_dir / "assets" / relative_path,
        meipass / relative_path,
        meipass / "assets" / relative_path,
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return relative_path

def encode_image_b64(path: str) -> str:
    return base64.b64encode(open(path, "rb").read()).decode()

# ----------------------------------------------------------------------
# 공통: STL 감소 / 병합 / 교차(BITE) / glb 변환
# ----------------------------------------------------------------------
def reduce_stl_size(file_path: str, out_folder: str, reduction_ratio: float = 0.875) -> str:
    """STL/PLY 파일 감소"""
    # 파일 확장자에 따라 적절한 reader 선택
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".ply":
        reader = vtk.vtkPLYReader()
        reader.SetFileName(file_path)
        reader.Update()
    else:  # .stl
        reader = vtk.vtkSTLReader()
        reader.SetFileName(file_path)
        reader.Update()

    # 메시 감소
    deci = vtk.vtkQuadricDecimation()
    deci.SetInputData(reader.GetOutput())
    deci.SetTargetReduction(reduction_ratio)
    deci.Update()

    # 출력 파일명 생성 (확장자는 원본 유지)
    basename = os.path.basename(file_path)
    out_path = os.path.join(out_folder, basename)

    # 파일 확장자에 따라 적절한 writer 선택
    if ext == ".ply":
        writer = vtk.vtkPLYWriter()
        writer.SetFileName(out_path)
        writer.SetInputData(deci.GetOutput())
        writer.Write()
    else:  # .stl
        writer = vtk.vtkSTLWriter()
        writer.SetFileName(out_path)
        writer.SetInputData(deci.GetOutput())
        writer.SetFileTypeToBinary()
        writer.Write()

    return out_path

def _merge_polydata(paths: list[str]) -> Optional[vtk.vtkPolyData]:
    """STL/PLY 파일들을 병합"""
    if not paths:
        return None
    append = vtk.vtkAppendPolyData()
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        if ext == ".ply":
            r = vtk.vtkPLYReader()
        else:  # .stl
            r = vtk.vtkSTLReader()
        r.SetFileName(p)
        r.Update()
        append.AddInputData(r.GetOutput())
    append.Update()
    clean = vtk.vtkCleanPolyData()
    clean.SetInputData(append.GetOutput())
    clean.Update()
    return clean.GetOutput()

def generate_bite_stl(paths_a: list[str], paths_b: list[str],
                      out_folder: str, tolerance: float = 0.01) -> Optional[str]:
    if not paths_a or not paths_b:
        return None
    pd1 = _merge_polydata(paths_a); pd2 = _merge_polydata(paths_b)
    if pd1 is None or pd2 is None:
        return None
    bf = vtk.vtkBooleanOperationPolyDataFilter(); bf.SetOperationToIntersection()
    bf.SetInputData(0, pd1); bf.SetInputData(1, pd2)
    if hasattr(bf, "SetTolerance"): bf.SetTolerance(tolerance)
    bf.Update()
    if bf.GetOutput().GetNumberOfPoints() == 0:  # 교차 없음
        return None
    bite_path = os.path.join(out_folder, "BITE_reduced.stl")
    w = vtk.vtkSTLWriter(); w.SetFileName(bite_path); w.SetInputData(bf.GetOutput()); w.SetFileTypeToBinary(); w.Write()
    return bite_path

def convert_stl_to_gltf(file_path: str) -> str:
    mesh = trimesh.load_mesh(file_path)
    return base64.b64encode(mesh.export(file_type='glb')).decode().strip()

# ==============================================================================
# 공통: 그룹/표시/치아번호 유틸 (치식 정규식 강화)
# ==============================================================================
FDI_ORDER = [
    18,17,16,15,14,13,12,11, 21,22,23,24,25,26,27,28,
    38,37,36,35,34,33,32,31, 41,42,43,44,45,46,47,48,
]
UPPER_SET = set(range(11, 29))   # 11–28
LOWER_SET = set(range(31, 49))   # 31–48
FDI_SINGLE_RE = re.compile(r"\b(1[1-8]|2[1-8]|3[1-8]|4[1-8])\b")
FDI_RANGE_RE  = re.compile(r"\b(1[1-8]|2[1-8]|3[1-8]|4[1-8])\s*-\s*(1[1-8]|2[1-8]|3[1-8]|4[1-8])\b")

def _expand_range(a: int, b: int) -> List[int]:
    """FDI_ORDER 순서를 따라 a..b 구간 확장"""
    try:
        i1, i2 = FDI_ORDER.index(a), FDI_ORDER.index(b)
        lo, hi = (i1, i2) if i1 <= i2 else (i2, i1)
        return FDI_ORDER[lo:hi+1]
    except ValueError:
        return [a, b]

def extract_fdi_teeth(text: str) -> List[int]:
    """
    문자열에서 FDI 치식(11–48)만 추출한다.
    - 'YYYY‑MM‑DD' 같은 날짜는 제외
    - '11-17' 형태의 범위는 FDI 범위일 때만 확장
    - 중복 제거(순서는 크게 중요치 않으므로 set 기반으로 단순화)
    """
    if not text:
        return []
    s = str(text)

    # 1) 범위를 먼저 처리 (날짜는 정규식에 안 걸림)
    teeth: list[int] = []
    used_pairs: set[Tuple[int, int]] = set()
    for m in FDI_RANGE_RE.finditer(s):
        a, b = int(m.group(1)), int(m.group(2))
        used_pairs.add((a, b))
        teeth.extend(_expand_range(a, b))

    # 2) 단일 치식 수집
    for m in FDI_SINGLE_RE.finditer(s):
        t = int(m.group(1))
        teeth.append(t)

    # 3) 중복 제거
    uniq = []
    seen = set()
    for t in teeth:
        if t not in seen:
            seen.add(t); uniq.append(t)
    return uniq

def determine_jaw(tooth_numbers: List[int]) -> str:
    if not tooth_numbers: return "mixed"
    if all(t in UPPER_SET for t in tooth_numbers): return "upper"
    if all(t in LOWER_SET for t in tooth_numbers): return "lower"
    return "mixed"

# ==============================================================================
# 3SHAPE (기존) – 분석/매핑
# ==============================================================================
XML_NS_3OX = {"ns": "http://schemas.3shape.com/3OX/OrderInterface/2011/01"}

def analyze_folder_3shape(folder: Path) -> pd.DataFrame:
    ox_files = list(folder.glob("*.3ox"))
    if not ox_files:
        raise FileNotFoundError(".3ox 파일이 없습니다.")
    order_no = ""
    for ox in ox_files:
        root = ET.parse(ox).getroot()
        n = root.find(".//ns:ThreeShapeOrderNo", XML_NS_3OX)
        if n is not None and n.text:
            order_no = n.text.strip(); break

    abuts = []
    for ox in ox_files:
        root = ET.parse(ox).getroot()
        for model in root.findall(".//ns:ModelElement", XML_NS_3OX):
            disp = model.attrib.get("displayName", "")
            idx_el = model.find("ns:ModelElementIndex", XML_NS_3OX)
            if idx_el is None: continue
            if "어버트먼트" in disp:
                teeth = set(extract_fdi_teeth(disp))
                abuts.append({"display": disp, "teeth": teeth, "index": idx_el.text.strip()})

    xml_names = {p.name for p in folder.glob("*.xml")}
    stl_names = {p.name for p in folder.glob("*.stl")}

    rows = []
    for ox in ox_files:
        root = ET.parse(ox).getroot()
        for model in root.findall(".//ns:ModelElement", XML_NS_3OX):
            disp = model.attrib.get("displayName", "")
            idx_el = model.find("ns:ModelElementIndex", XML_NS_3OX)
            if idx_el is None: continue
            idx_val = idx_el.text.strip()

            if "어버트먼트" in disp: cat = "Abut"
            elif "브릿지" in disp:  cat = "Bridge"
            elif "크라운" in disp:  cat = "Crown"
            else:                   cat = "Other"

            teeth = extract_fdi_teeth(disp)
            jaw_ko = "상악" if determine_jaw(teeth) == "upper" else "하악" if determine_jaw(teeth) == "lower" else "혼합"
            matched_xmls = []
            if cat in ("Crown","Bridge"):
                for ab in abuts:
                    if set(teeth) & ab["teeth"]:
                        xml_file = f"ImplantDirectionPosition_{ab['index']}.xml"
                        if xml_file in xml_names:
                            matched_xmls.append(xml_file)
            stl_guess = f"{order_no}_{idx_val}.stl"
            stl_file = stl_guess if stl_guess in stl_names else ""
            rows.append({"Display Name":disp, "Category":cat, "Jaw":jaw_ko, "STL Filename":stl_file, "Matched Abutment XMLs":", ".join(matched_xmls)})
    df = pd.DataFrame(rows)
    if df.empty: raise ValueError("분석 결과가 비어있습니다.")
    return df

def export_to_excel(df: pd.DataFrame, out_path: Path) -> None:
    out_path = out_path.with_suffix(".xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="All")
        df[df["Jaw"] == "상악"].to_excel(writer, index=False, sheet_name="Maxilla")
        df[df["Jaw"] == "하악"].to_excel(writer, index=False, sheet_name="Mandible")

def _read_3ox(folder: str) -> Optional[str]:
    oxfile = next((os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".3ox")), None)
    if not oxfile: return None
    data = open(oxfile, "rb").read()
    for enc in ("utf-16","utf-8"):
        try: return data.decode(enc)
        except Exception: pass
    return None

def parse_3ox_for_groups(folder: str) -> dict:
    excel_mapping: dict[str,str] = {}
    try:
        xls_path = next((p for p in Path(folder).glob("*.xlsx") if "parsed_3shape" in p.name.lower()), None)
        if xls_path:
            df = pd.read_excel(xls_path, sheet_name="All")
            for _, row in df.iterrows():
                stl = str(row.get("STL Filename", "")).strip()
                if not stl: continue
                cat = str(row.get("Category","")).lower(); jaw_ko = str(row.get("Jaw","")).strip()
                jaw = "upper" if jaw_ko.startswith("상") else "lower" if jaw_ko.startswith("하") else "mixed"
                if cat.startswith("abut"): g = f"{jaw}_abutment" if jaw in ("upper","lower") else "etc"
                elif cat in ("crown","bridge"): g = f"{jaw}_crownbridge" if jaw in ("upper","lower") else "etc"
                else: g = "etc"
                excel_mapping[stl] = g
                if stl.lower().endswith(".stl"): excel_mapping[stl[:-4]+"_reduced.stl"] = g
    except Exception as e:
        print(f"[WARN] Excel 매핑 건너뜀: {e}")

    base_map = dict(excel_mapping)
    txt = _read_3ox(folder)
    if not txt: return base_map
    root = ET.fromstring(txt)
    ns = {"ns": root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
    order_no = root.findtext(".//ns:ThreeShapeOrderNo", default="", namespaces=ns).strip()

    def _get_stl(el) -> str:
        tag = el.findtext("ns:ModelFileName", default="", namespaces=ns).strip()
        if tag: return os.path.basename(tag)
        idx = el.findtext("ns:ModelElementIndex", default="", namespaces=ns).strip()
        return f"{order_no}_{idx}.stl" if idx else ""

    def _classify_category(display: str) -> str:
        dl = display.lower()
        if "어버트먼트" in display or "abutment" in dl: return "abutment"
        if ("브릿지" in display or "bridge" in dl) or ("크라운" in display or "crown" in dl): return "crownbridge"
        return "etc"

    for el in root.findall(".//ns:ModelElement", ns):
        disp = el.attrib.get("displayName","")
        stl  = _get_stl(el)
        if not stl or stl in base_map: continue
        cat = _classify_category(disp)
        jaw = determine_jaw(extract_fdi_teeth(disp))
        grp = f"{jaw}_{cat}" if jaw in ("upper","lower") and cat in ("abutment","crownbridge") else "etc"
        base_map[stl] = grp
        if stl.lower().endswith(".stl"): base_map[stl[:-4]+"_reduced.stl"] = grp

    # Scan 파일 대략 분류 (3shape: prep/ant 구분)
    prep_scans, ant_scans = [], []
    for el in root.findall(".//ns:ModelElement", ns):
        scanfiles = el.find("ns:ScanFiles", ns)
        if scanfiles is None: continue
        for sf in scanfiles.findall("ns:ScanFile", ns):
            n = os.path.basename(sf.attrib.get("path",""))
            if not n: continue
            lname = n.lower()
            if ("prep" in lname or "preparation" in lname) and "prepreparation" not in lname: prep_scans.append(n)
            elif ("antagonist" in lname or lname.startswith("ant")): ant_scans.append(n)
            if n.lower().endswith(".stl"):
                if n in prep_scans: prep_scans.append(n[:-4]+"_reduced.stl")
                elif n in ant_scans: ant_scans.append(n[:-4]+"_reduced.stl")

    has_upper = any(g.startswith("upper_") for g in base_map.values())
    has_lower = any(g.startswith("lower_") for g in base_map.values())
    both = has_upper and has_lower
    if both:
        for s in prep_scans + ant_scans:
            lname = s.lower()
            base_map[s] = "upper_scan" if "scan_1" in lname else "lower_scan"
    else:
        work = "upper" if has_upper else "lower"; oppo = "lower" if work=="upper" else "upper"
        for s in prep_scans: base_map[s] = f"{work}_scan"
        for s in ant_scans:  base_map[s] = f"{oppo}_scan"
    return base_map

def parse_3ox_for_display(folder: str) -> dict:
    dispmap: dict[str,str] = {}
    txt = _read_3ox(folder)
    if not txt: return dispmap
    root = ET.fromstring(txt)
    ns = {"ns": root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
    order_no = root.findtext(".//ns:ThreeShapeOrderNo", default="", namespaces=ns).strip()

    def add(name: str, display: str) -> None:
        if name:
            dispmap[name] = display or name
            if name.lower().endswith(".stl"):
                dispmap[name[:-4] + "_reduced.stl"] = display or name

    def _get_stl_filename_from_element(el, ns, order_no: str) -> str:
        stl_tag = el.findtext("ns:ModelFileName", default="", namespaces=ns)
        stl = os.path.basename(stl_tag.strip()) if stl_tag else ""
        if not stl:
            idx = el.findtext("ns:ModelElementIndex", default="", namespaces=ns).strip()
            if order_no and idx:
                stl = f"{order_no}_{idx}.stl"
        return stl

    for el in root.findall(".//ns:ModelElement", ns):
        disp = el.attrib.get("displayName","").strip()
        stl  = _get_stl_filename_from_element(el, ns, order_no)
        add(stl, disp)
        scanfiles = el.find("ns:ScanFiles", ns)
        if scanfiles is not None:
            for sf in scanfiles.findall("ns:ScanFile", ns):
                n = os.path.basename(sf.attrib.get("path",""))
                add(n, n)
    return dispmap

# ==============================================================================
# EXO (Exocad) – ZIP 처리/행렬/분석/매핑
# ==============================================================================

# ------------------------- modelInfo 기반 Jaw 추정 유틸 + 문자열 판정 ------------------
def _infer_jaw_from_string(s: str) -> Optional[str]:
    """문자열에서 상/하악 단서를 찾아 'upper'/'lower' 반환 (없으면 None)"""
    if not s:
        return None
    s = s.lower()
    if "상악" in s or any(k in s for k in ["upper", "maxilla", "upperjaw", "u_jaw", "u-jaw", "jaw_u", "_u", " uj "]):
        return "upper"
    if "하악" in s or any(k in s for k in ["lower", "mandible", "lowerjaw", "l_jaw", "l-jaw", "jaw_l", "_l", " lj "]):
        return "lower"
    jaw = determine_jaw(extract_fdi_teeth(s))
    if jaw in ("upper","lower"):
        return jaw
    return None

def build_mi_jaw_map(mi_root: Optional[ET.Element]) -> Dict[str, str]:
    """
    modelInfo XML을 훑어서 파일별 상/하악 정보를 추정한다.
    - Filename 하위 노드를 기준으로 해당 요소의 Label/Name/Jaw/JawType/UpperLower 등 텍스트를 모아 판정
    - 텍스트가 불충분하면 tag 이름/descendant 텍스트/파일명까지 모두 검사
    - 결과 키는 소문자 파일명(basename)으로 저장하며, *_reduced.stl 키도 함께 등록
    """
    mp: Dict[str, str] = {}
    if mi_root is None:
        return mp

    for elem in mi_root.iter():
        fn = elem.find("Filename")
        if fn is None or not (fn.text and fn.text.strip()):
            continue

        name = os.path.basename(fn.text.strip()).lower()
        texts: List[str] = []
        for key in ("Jaw","JawType","UpperLower","JawPosition","Type","Category",
                    "ComponentType","Label","Name","DisplayName","ModelType",
                    "BaseType","GingivaType"):
            v = elem.findtext(key)
            if v: texts.append(v)

        for sub in elem.iter():
            if sub.text: texts.append(sub.text)
            if sub.tag:  texts.append(sub.tag)

        jaw = _infer_jaw_from_string(" ".join(texts)) or _infer_jaw_from_string(name)
        if not jaw:
            continue
        mp[name] = jaw
        if name.endswith(".stl"):
            mp[name[:-4] + "_reduced.stl"] = jaw
    return mp
# -----------------------------------------------------------------------------

# 행렬 파싱 유틸
def parse_matrix(elem) -> 'np.ndarray':
    import numpy as np
    M = np.zeros((4, 4), dtype=float)
    ok = True
    for i in range(4):
        for j in range(4):
            tag = f"_{i}{j}"
            value = elem.find(tag)
            if value is None or value.text is None:
                ok = False
                break
            M[i, j] = float(value.text)
        if not ok: break
    if ok:
        return M

    # m00..m33 패턴
    lab_ok = True
    M2 = np.zeros((4,4), dtype=float)
    for i in range(4):
        for j in range(4):
            tag = f"m{i}{j}"
            value = elem.find(tag)
            if value is None or value.text is None:
                lab_ok = False
                break
            M2[i, j] = float(value.text)
        if not lab_ok: break
    if lab_ok:
        return M2

    # 텍스트에 16개 숫자
    txt = "".join(list(elem.itertext())).strip()
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", txt)
    if len(nums) >= 16:
        arr = list(map(float, nums[:16]))
        return np.array(arr, dtype=float).reshape((4,4))

    return None

def parse_matrix3(elem) -> 'np.ndarray|None':
    import numpy as np
    if elem is None: return None
    R = np.zeros((3,3), dtype=float)
    ok = True
    for i in range(3):
        for j in range(3):
            tag = f"_{i}{j}"
            value = elem.find(tag)
            if value is None or value.text is None:
                ok = False; break
            R[i,j] = float(value.text)
        if not ok: break
    if ok: return R
    txt = "".join(list(elem.itertext())).strip()
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", txt)
    if len(nums) >= 9:
        arr = list(map(float, nums[:9]))
        return np.array(arr, dtype=float).reshape((3,3))
    return None

def parse_vec3(elem) -> 'np.ndarray|None':
    import numpy as np
    if elem is None: return None
    vals = []
    for k in ("_0","_1","_2"):
        n = elem.find(k)
        if n is not None and n.text is not None:
            vals.append(float(n.text))
    if len(vals) == 3:
        return np.array(vals, dtype=float)
    vals = []
    for k in ("x","y","z"):
        n = elem.find(k)
        if n is not None and n.text is not None:
            vals.append(float(n.text))
    if len(vals) == 3:
        return np.array(vals, dtype=float)
    txt = "".join(list(elem.itertext())).strip()
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", txt)
    if len(nums) >= 3:
        return np.array(list(map(float, nums[:3])), dtype=float)
    return None

def convert_matrix_to_row_major(M_col):
    import numpy as np
    return M_col.T

def compute_inverse(M):
    import numpy as np
    return np.linalg.inv(M)

# ---- constructionInfo 기반 파일별/글로벌 행렬 ----
def find_exo_transform_matrix_ci(xml_root, stl_name: str):
    if xml_root is None:
        import numpy as np
        return np.identity(4)

    global_T_inv = None
    global_elem = xml_root.find("MatrixToScanDataFiles")
    if global_elem is not None:
        M_col = parse_matrix(global_elem)
        if M_col is not None:
            M = convert_matrix_to_row_major(M_col)
            global_T_inv = compute_inverse(M)

    file_T_inv = None
    cf_list = xml_root.find("ConstructionFileList")
    if cf_list is not None:
        for cf in cf_list.findall("ConstructionFile"):
            fname_elem = cf.find("Filename")
            if fname_elem is not None and fname_elem.text and os.path.basename(stl_name).lower() in os.path.basename(fname_elem.text).lower():
                cand = cf.find("ZRotationMatrix")
                if cand is not None:
                    M_col = parse_matrix(cand)
                    if M_col is not None:
                        M = convert_matrix_to_row_major(M_col)
                        file_T_inv = compute_inverse(M)
                        break
                R = parse_matrix3(cf.find("RotationMatrix"))
                t = parse_vec3(cf.find("Translation")) or parse_vec3(cf.find("Offset"))
                if R is not None or t is not None:
                    import numpy as np
                    M = np.eye(4)
                    if R is not None: M[:3,:3] = R
                    if t is not None: M[:3, 3] = t
                    file_T_inv = compute_inverse(convert_matrix_to_row_major(M))
                    break

    import numpy as np
    if global_T_inv is None and file_T_inv is None:
        return np.identity(4)
    if global_T_inv is None: return file_T_inv
    if file_T_inv  is None: return global_T_inv
    return global_T_inv @ file_T_inv

# ---- modelInfo 기반 파일별/글로벌 행렬 ----
def find_exo_transform_matrix_mi(xml_root, stl_name: str):
    if xml_root is None:
        import numpy as np
        return np.identity(4)

    global_T_inv = None
    for tag in ("MatrixToScanDataFiles", "GlobalMatrix", "MainMatrix", "ModelMatrix", "WorldMatrix"):
        ge = xml_root.find(tag)
        if ge is None: continue
        M_col = parse_matrix(ge)
        if M_col is not None:
            M = convert_matrix_to_row_major(M_col)
            global_T_inv = compute_inverse(M)
            break

    file_T_inv = None
    stl_name_only = os.path.basename(stl_name).lower()
    for elem in xml_root.iter():
        fn = elem.find("Filename")
        if fn is None or not (fn.text and stl_name_only in os.path.basename(fn.text).lower()):
            continue

        for cand_name in ("TransformationMatrix","ZRotationMatrix","Matrix","ModelMatrix","MeshMatrix","LocalMatrix"):
            m_elem = elem.find(cand_name)
            if m_elem is None: continue
            M_col = parse_matrix(m_elem)
            if M_col is not None:
                M = convert_matrix_to_row_major(M_col)
                file_T_inv = compute_inverse(M)
                break
        if file_T_inv is not None:
            break

        R = parse_matrix3(elem.find("RotationMatrix")) or parse_matrix3(elem.find("Rotation"))
        t = (parse_vec3(elem.find("Translation")) or
             parse_vec3(elem.find("TranslationVector")) or
             parse_vec3(elem.find("Offset")) or
             parse_vec3(elem.find("T")))
        if R is not None or t is not None:
            import numpy as np
            M = np.eye(4)
            if R is not None: M[:3,:3] = R
            if t is not None: M[:3, 3] = t
            file_T_inv = compute_inverse(convert_matrix_to_row_major(M))
            break

    import numpy as np
    if global_T_inv is None and file_T_inv is None:
        return np.identity(4)
    if global_T_inv is None: return file_T_inv
    if file_T_inv  is None: return global_T_inv
    return global_T_inv @ file_T_inv

def _find_exo_files(folder: str) -> Tuple[Optional[str], Optional[str]]:
    ci = None; mi = None
    for f in os.listdir(folder):
        l = f.lower()
        p = os.path.join(folder, f)
        if os.path.isfile(p):
            if l.endswith(".constructioninfo") or (l.endswith(".xml") and "constructioninfo" in l):
                ci = p
            elif l.endswith(".modelinfo") or (l.endswith(".xml") and "modelinfo" in l):
                mi = p
    return ci, mi

def _extract_zips_to_temp(base_folder: str) -> list[str]:
    extracted_folders: list[str] = []
    zips = [os.path.join(base_folder, z) for z in os.listdir(base_folder) if z.lower().endswith(".zip")]
    if not zips:
        return extracted_folders
    tmp_root = tempfile.mkdtemp(prefix="dlas_zip_")
    for z in zips:
        try:
            base = os.path.splitext(os.path.basename(z))[0]
            out_dir = os.path.join(tmp_root, base)
            os.makedirs(out_dir, exist_ok=True)
            with zipfile.ZipFile(z, 'r') as zip_ref:
                zip_ref.extractall(out_dir)
            extracted_folders.append(out_dir)
        except Exception as e:
            print(f"[WARN] ZIP 해제 실패: {z} – {e}")
    return extracted_folders

def detect_mode(folder: str) -> str:
    has_3ox = any(fn.lower().endswith(".3ox") for fn in os.listdir(folder))
    if has_3ox: return "3shape"
    ci, mi = _find_exo_files(folder)
    if ci or mi: return "exo"
    return "none"

def parse_exo_for_groups(folder: str) -> dict:
    """
    EXO 그룹 맵 생성 (jaw_category)
    - 파일명 및 modelInfo/constructionInfo 단서 기반
    - 이름 기반 규칙:
       · *upperjaw* → upper_scan
       · *lowerjaw* → lower_scan
       · *occlusion* → etc
       · *modelgingiva*, *modelbase*, *gingiva*, *base* → (상/하 추정 후) *_scan
       · *marker* → scan (변경)
       · *abut*, *scanbody*, *ti-base*, *tibase* → *_abutment
    - [우선순위] 파일명 치식 > modelInfo 추정 > 이름 휴리스틱
    """
    group_map: dict[str,str] = {}

    # ---- CI/MI 루트 둘 다 파싱 ----
    ci, mi = _find_exo_files(folder)
    ci_root = None
    mi_root = None
    if ci:
        try: ci_root = ET.parse(ci).getroot()
        except Exception as e: print("[WARN] constructionInfo parse 실패:", e)
    if mi:
        try: mi_root = ET.parse(mi).getroot()
        except Exception as e: print("[WARN] modelInfo parse 실패:", e)

    # 1) 기본: 폴더 내 STL/PLY 전수조사
    stls = [f for f in os.listdir(folder) if f.lower().endswith((".stl", ".ply"))]

    # 1-1) modelInfo 기반 Jaw 맵(파일명→upper/lower)
    mi_jaw_map = build_mi_jaw_map(mi_root)  # 키는 '소문자 basename' + *_reduced.stl 포함

    def decide_cat(name: str) -> str:
        l = name.lower()
        if "occlusion" in l: return "etc"
        if "upperjaw" in l or "lowerjaw" in l: return "scan"
        if any(k in l for k in ("modelgingiva","modelbase","gingiva","model","base")): return "scan"
        if "marker" in l: return "scan"
        if any(k in l for k in ("abut","scanbody","tibase","ti-base")): return "abutment"
        if any(k in l for k in ("crown","bridge","pontic","coping","framework","veneer")): return "crownbridge"
        if "prep" in l or "preparation" in l: return "scan"
        if "antagonist" in l or "oppos" in l or l.startswith("ant"): return "scan"
        return "etc"

    def decide_jaw_fallback(name: str) -> str:
        # 문자열 키워드 기반(상/하악 한글/영문) → 치식 추정
        jaw = _infer_jaw_from_string(name)
        if jaw: return jaw
        # 최종 모호하면 upper
        return "upper"

    for s in stls:
        s_key = s.lower()
        cat = decide_cat(s)

        # 1) 파일명에서 치식 우선
        teeth = extract_fdi_teeth(s)
        jaw_by_teeth = determine_jaw(teeth)

        if jaw_by_teeth in ("upper","lower"):
            jaw = jaw_by_teeth
        # 2) modelInfo의 Jaw 추정(모델/베이스/gingiva/scan 계열 우선 적용)
        elif (cat == "scan" or any(k in s_key for k in ("modelgingiva","gingiva","modelbase","base"))) and s_key in mi_jaw_map:
            jaw = mi_jaw_map[s_key]
        # 3) 이름 휴리스틱
        else:
            jaw = decide_jaw_fallback(s)

        grp = f"{jaw}_{cat}" if jaw in ("upper","lower") and cat in ("abutment","crownbridge","scan") else "etc"
        group_map[s] = grp
        # 확장자 유지하면서 _reduced 추가
        base = os.path.splitext(s)[0]
        ext = os.path.splitext(s)[1]
        group_map[base + "_reduced" + ext] = grp

    return group_map

def parse_exo_for_display(folder: str) -> dict:
    disp: dict[str,str] = {}
    for s in os.listdir(folder):
        if s.lower().endswith((".stl", ".ply")):
            base = os.path.splitext(s)[0]
            ext = os.path.splitext(s)[1]  # 확장자 유지
            disp[s] = base
            disp[base + "_reduced" + ext] = base

    ci, mi = _find_exo_files(folder)
    try:
        src = ci or mi
        if src:
            root = ET.parse(src).getroot()
            cfl = root.find("ConstructionFileList")
            if cfl is not None:
                for cf in cfl.findall("ConstructionFile"):
                    fn = (cf.findtext("Filename") or "").strip()
                    lab = (cf.findtext("Label") or cf.findtext("Name") or "").strip()
                    if not fn: continue
                    name = os.path.basename(fn)
                    if name in disp and lab:
                        disp[name] = lab
                        disp[name[:-4]+"_reduced.stl"] = lab
    except Exception as e:
        print("[WARN] EXO display parse 실패:", e)
    return disp


# ==== EXO 파일 소유 판정 및 단일 변환 선택 유틸 =============================
def _ci_has_file_for_stl(ci_root: Optional[ET.Element], stl_name: str) -> bool:
    if ci_root is None:
        return False
    cfl = ci_root.find("ConstructionFileList")
    if cfl is None:
        return False
    target = os.path.basename(stl_name).lower()
    for cf in cfl.findall("ConstructionFile"):
        fn = cf.find("Filename")
        if fn is not None and fn.text:
            if target in os.path.basename(fn.text).lower():
                return True
    return False

def _mi_has_file_for_stl(mi_root: Optional[ET.Element], stl_name: str) -> bool:
    if mi_root is None:
        return False
    target = os.path.basename(stl_name).lower()
    for elem in mi_root.iter():
        fn = elem.find("Filename")
        if fn is not None and fn.text:
            if target in os.path.basename(fn.text).lower():
                return True
    return False

def _looks_model_component(stl_name: str) -> bool:
    l = stl_name.lower()
    return any(k in l for k in (
        "modelgingiva", "gingiva", "modelbase", "base",
        "upperjaw", "lowerjaw", "_jaw", "jaw_"
    ))

def _decide_owner(ci_root: Optional[ET.Element], mi_root: Optional[ET.Element], stl_name: str) -> str | None:
    ci_has = _ci_has_file_for_stl(ci_root, stl_name)
    mi_has = _mi_has_file_for_stl(mi_root, stl_name)
    if ci_has and not mi_has:
        return "ci"
    if mi_has and not ci_has:
        return "mi"
    if ci_has and mi_has:
        return "both"
    return None

def get_exo_transform_matrix(ci_root: Optional[ET.Element],
                             mi_root: Optional[ET.Element],
                             stl_name: str):
    import numpy as np
    owner = _decide_owner(ci_root, mi_root, stl_name)
    if owner == "ci":
        return find_exo_transform_matrix_ci(ci_root, stl_name)
    if owner == "mi":
        return find_exo_transform_matrix_mi(mi_root, stl_name)
    if owner == "both":
        if _looks_model_component(stl_name):
            return find_exo_transform_matrix_mi(mi_root, stl_name)
        return find_exo_transform_matrix_ci(ci_root, stl_name)
    return np.identity(4)

def exo_transform_if_possible(stl_path: str,
                              ci_root: Optional[ET.Element],
                              mi_root: Optional[ET.Element],
                              xfm_out_dir: str) -> str:
    try:
        name = os.path.basename(stl_path)
        import numpy as np
        T = get_exo_transform_matrix(ci_root, mi_root, name)
        if np.allclose(T, np.eye(4)):
            return stl_path
        mesh = trimesh.load_mesh(stl_path)
        mesh.apply_transform(T)
        out_path = os.path.join(xfm_out_dir, name)  # 이름 보존
        mesh.export(out_path)
        return out_path
    except Exception as e:
        print(f"[WARN] 변환행렬 적용 실패({os.path.basename(stl_path)}): {e}")
        return stl_path


# ==============================================================================
# HTML 템플릿
# ==============================================================================
def generate_html(model_infos: list[dict[str, str]],
                  annos_json: str,
                  user_logo_b64: str | None = None) -> str:
    group_color_map = {
        "upper_crownbridge": 0xFFFFF0,
        "upper_abutment":    0xC0C0C0,
        "upper_scan":        0xF5DEB3,
        "lower_crownbridge": 0xFFFAF0,
        "lower_abutment":    0xA9A9A9,
        "lower_scan":        0xFFDEAD,
        "bite":              0xFF0000,
        "etc":               0xCCCCCC,
        "annotation":        0xFFFF00
    }
    js_colormap = json.dumps(group_color_map)

    logo_b64 = None
    logo_path = resource_path("white logo.jpg")
    if logo_path:
        try: logo_b64 = encode_image_b64(logo_path)
        except Exception: pass

    top_logo_html = ""
    if logo_b64:
        top_logo_html = (f'<img id="topLogo" src="data:image/jpeg;base64,{logo_b64}" '
                         f'style="position:absolute;top:10px;left:50%;transform:translateX(-50%);'
                         f'height:120px;z-index:99;user-select:none;" alt="DLAS Logo"/>')

    user_logo_html = ""
    if user_logo_b64:
        user_logo_html = (f'<img id="userLogo" src="data:image;base64,{user_logo_b64}" '
                          f'style="position:absolute;bottom:10px;left:10px;max-width:160px;max-height:70px;'
                          f'z-index:99;user-select:none;" alt="User Logo"/>')

    def esc(s: str) -> str:
        return (s.replace("\\", "\\\\")
                 .replace("'", "\\'")
                 .replace("</", "<\\/")
                 .replace("\n", "").replace("\r", ""))

    js_models = ",\n      ".join(
        "{{name:'{n}',b64:'{b}',group:'{g}',displayName:{d}}}".format(
            n=esc(m["name"]), b=esc(m["b64"]), g=m["group"],
            d=json.dumps(m.get("displayName") or m["name"])
        ) for m in model_infos
    )

    html_tpl = Template(r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
<title>DLAS STL Viewer</title>
<!--
  This viewer uses three.js (MIT License)
  Copyright © 2010-2024 Three.js authors
  https://github.com/mrdoob/three.js/blob/master/LICENSE
-->
<script>
const _BASE_HTML = document.documentElement.cloneNode(true).outerHTML;
const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth <= 768;
</script>
<script src="https://cdn.jsdelivr.net/npm/three@0.137.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.137.0/examples/js/loaders/GLTFLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.137.0/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.137.0/examples/js/controls/TrackballControls.js"></script>
<style>
  body{margin:0;overflow:hidden;font-family:Arial,Helvetica,sans-serif;background:#F5F5F5;}
  #viewer{width:100vw;height:100vh;}

  /* ========== PC 스타일 (기본) ========== */
  #groupPanel{position:absolute;top:90px;left:10px;background:rgba(255,255,255,.97);padding:14px;border-radius:8px;
    z-index:99;max-width:420px;font-size:15px;box-shadow:0 4px 10px #0001;user-select:none;transition:transform 0.3s ease;}
  .group>.children{margin-left:5px;margin-bottom:3px;}
  .subgroup>.children{margin-left:5px;}
  .collapseBtn{background:#eee;border:1px solid #ccc;border-radius:3px;width:20px;height:20px;font-size:12px;
    cursor:pointer;margin-right:3px;padding:0;vertical-align:middle;}
  .groupToggle,.subgroupToggle,.modelToggle{background:#198754;color:#fff;border:none;border-radius:4px;font-size:12px;margin-left:8px;
    cursor:pointer;padding:2px 6px;}
  .modelEdit,.modelDelete{display:none;}  /* EditGrp, Del 버튼 숨김 */
  .groupToggle.off,.subgroupToggle.off,.modelToggle.off{background:#d1d5db;color:#444;}
  .modelitem{margin-bottom:2px;white-space:nowrap;}
  .modelitem span,.grpName,.subName,.allName{display:inline-block;min-width:120px;cursor:default;}  /* 텍스트 드래그 제거 */

  /* 투명도 슬라이더 스타일 (ON/OFF 버튼 옆에 배치 - 검정색) */
  .opacity-slider{
    display:inline-block;
    width:70px;
    height:5px;
    -webkit-appearance:none;
    appearance:none;
    background:linear-gradient(to right, rgba(0,0,0,0.2) 0%, rgba(0,0,0,1) 100%);
    border-radius:3px;
    outline:none;
    margin:0 4px;
    vertical-align:middle;
    cursor:pointer;
  }
  .opacity-slider::-webkit-slider-thumb{
    -webkit-appearance:none;
    appearance:none;
    width:12px;
    height:12px;
    background:#333;
    border-radius:50%;
    cursor:pointer;
    border:1px solid #fff;
  }
  .opacity-slider::-moz-range-thumb{
    width:12px;
    height:12px;
    background:#333;
    border-radius:50%;
    cursor:pointer;
    border:1px solid #fff;
  }
  #topButtons{position:absolute;top:50px;left:10px;z-index:100;}
  #topButtons button{background:#555;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:12px;margin-right:6px;cursor:pointer;}
  #addAnnoBtn{position:absolute;top:10px;right:10px;background:#2962ff;color:#fff;border:none;border-radius:4px;padding:5px 10px;font-size:13px;z-index:100;cursor:pointer;}
  #addAnnoBtn.active{background:#ff6f00;}
  .annotation{position:absolute;background:rgba(255,255,0,.85);padding:2px 4px;border-radius:3px;font-size:12px;
    color:#000;font-weight:bold;border:1px solid #999;cursor:pointer;}
  #groupSelectModal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;backdrop-filter:blur(2px);
    background:rgba(0,0,0,.35);z-index:300;align-items:center;justify-content:center;}
  #groupSelectBox{background:#fff;padding:18px 22px 22px;border-radius:8px;min-width:260px;text-align:center;box-shadow:0 4px 12px #0003;}
  #groupSelectBox button{display:block;margin:6px auto;padding:6px 12px;font-size:14px;border:none;border-radius:4px;cursor:pointer;background:#2d6cdf;color:#fff;}
  #groupSelectBox .cancelBtn{background:#777;}
  .annoMenu{position:absolute;background:#fefefe;border:1px solid #ccc;border-radius:4px;padding:4px;z-index:400;box-shadow:0 4px 8px #0002;}
  .annoMenu button{display:block;width:100%;border:none;background:#fff;padding:4px 10px;font-size:13px;text-align:left;cursor:pointer;}
  .annoMenu button:hover{background:#eee;}
  #viewSavePanel{position:absolute;bottom:60px;right:10px;display:flex;flex-direction:column;align-items:flex-end;z-index:100;}
  #saveViewBtn{background:#007bff;color:#fff;border:none;border-radius:4px;padding:4px 8px;font-size:12px;margin-bottom:6px;cursor:pointer;}
  .viewBtn{background:#eee;border:1px solid #ccc;border-radius:4px;padding:2px 6px;font-size:11px;margin-bottom:3px;cursor:pointer;}
  #dlasHomeBtn{position:fixed;bottom:10px;right:10px;z-index:150;background:#1565c0;color:#fff;padding:10px 24px;
    font-size:15px;border-radius:9999px;font-weight:bold;box-shadow:0 2px 10px #0002;border:none;cursor:pointer;transition:.2s;}
  #dlasHomeBtn:hover{background:#00bcd4;color:#222;}

  /* 모바일 토글 버튼 (하단 고정) */
  #mobileToggleBtn{display:none;position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
    background:#198754;color:#fff;border:none;border-radius:25px;padding:12px 30px;font-size:16px;font-weight:bold;
    box-shadow:0 4px 12px rgba(0,0,0,0.3);z-index:200;cursor:pointer;touch-action:manipulation;}
  #mobileToggleBtn:active{transform:translateX(-50%) scale(0.95);}

  /* ========== 모바일 스타일 ========== */
  @media (max-width: 768px) {
    /* 터치 드래그 방지 */
    body{
      -webkit-user-select:none;
      user-select:none;
      -webkit-touch-callout:none;
      touch-action:pan-x pan-y;
    }

    /* 그룹 패널을 좌측 슬라이딩 패널로 변경 (배경 투명, 너비 축소) */
    #groupPanel{
      position:fixed;
      top:0 !important;
      bottom:0;
      left:0;
      right:auto;
      max-width:70vw !important;
      width:70vw;
      height:100vh;
      max-height:100vh;
      overflow-y:auto;
      border-radius:0;
      padding:70px 12px 16px 12px;
      font-size:14px;
      transform:translateX(-100%);
      background:transparent !important;
      box-shadow:none;
      -webkit-user-select:none;
      user-select:none;
    }
    #groupPanel.mobile-open{transform:translateX(0);}

    /* 그룹과 항목에 클릭 가능한 투명 배경 추가 */
    .group{
      background:transparent;
      border-radius:8px;
      padding:8px;
      margin-bottom:8px;
      box-shadow:none;
    }
    .subgroup{
      background:transparent;
      border-radius:6px;
      padding:6px;
      margin:4px 0;
    }
    .modelitem{
      background:transparent;
      border-radius:4px;
      padding:6px 8px;
      margin-bottom:4px;
      line-height:1.4;
      box-shadow:none;
      display:flex;
      flex-wrap:wrap;
      align-items:center;
      gap:4px;
    }
    .modelitem span{
      flex:1 1 100%;
      min-width:100%;
      font-size:11px;
      word-wrap:break-word;
      white-space:normal;
      order:-1;
    }
    .modelitem .modelToggle{
      flex:0 0 auto;
    }
    .modelitem .opacity-slider{
      flex:1 1 auto;
      min-width:70px;
    }

    /* 버튼 크기 30% 축소 (기존 대비 추가 10% 축소) */
    .groupToggle,.subgroupToggle,.modelToggle{font-size:11px;padding:5px 9px;margin-left:4px;min-height:30px;}
    .modelEdit,.modelDelete{display:none !important;}  /* 모바일에서 EditGrp과 Del 버튼 숨김 */
    .collapseBtn{width:26px;height:26px;font-size:13px;min-height:30px;}
    .modelitem span,.grpName,.subName,.allName{min-width:60px;font-size:11px;cursor:default;}  /* 텍스트 드래그 제거 */

    /* 투명도 슬라이더 스타일 (ON/OFF 버튼 옆에 배치 - 검정색) */
    .opacity-slider{
      display:inline-block !important;
      flex:0 0 70px !important;
      width:70px !important;
      height:5px !important;
      -webkit-appearance:none;
      appearance:none;
      background:linear-gradient(to right, rgba(0,0,0,0.2) 0%, rgba(0,0,0,1) 100%) !important;
      border-radius:3px;
      outline:none;
      margin:0 2px !important;
      vertical-align:middle;
      cursor:pointer;
    }
    .opacity-slider::-webkit-slider-thumb{
      -webkit-appearance:none;
      appearance:none;
      width:18px !important;
      height:18px !important;
      background:#000 !important;
      border:2px solid white !important;
      border-radius:50%;
      cursor:pointer;
      box-shadow:0 2px 5px rgba(0,0,0,0.5);
      transition:transform 0.1s;
    }
    .opacity-slider::-webkit-slider-thumb:active{
      transform:scale(1.2);
    }
    .opacity-slider::-moz-range-thumb{
      width:18px !important;
      height:18px !important;
      background:#000 !important;
      border:2px solid white !important;
      border-radius:50%;
      cursor:pointer;
      box-shadow:0 2px 5px rgba(0,0,0,0.5);
    }

    /* 상단 버튼들 조정 */
    #topButtons{top:10px;left:10px;display:flex;gap:6px;}
    #topButtons button{font-size:14px;padding:8px 14px;min-height:44px;}
    #addAnnoBtn{top:10px;right:10px;font-size:15px;padding:10px 16px;min-height:44px;}

    /* 모바일에서는 Save, Annotation, View 버튼 숨김 */
    #topButtons{display:none;}
    #addAnnoBtn{display:none;}
    #viewSavePanel{display:none;}

    /* 홈 버튼: 우측 하단으로 이동 */
    #dlasHomeBtn{
      bottom:20px !important;
      top:auto !important;
      right:20px !important;
      left:auto !important;
      transform:none !important;
      padding:10px 20px;
      font-size:14px;
      z-index:150;
    }

    /* 모바일 토글 버튼: 좌측 상단으로 이동 (햄버거 메뉴처럼) */
    #mobileToggleBtn{
      display:block;
      bottom:auto !important;
      top:15px !important;
      left:15px !important;
      right:auto !important;
      transform:none !important;
      padding:10px 18px;
      font-size:15px;
      border-radius:8px;
      z-index:200;
    }

    /* DLAS 로고: 상단 중앙 (헤더 바로 밑) */
    #topLogo{
      top:10px !important;
      left:50% !important;
      transform:translateX(-50%) !important;
      max-width:70vw !important;
      height:auto !important;
      max-height:50px !important;
      width:auto !important;
    }

    /* 사용자 로고: 좌측 하단 (dlas.io 버튼과 겹치지 않게) */
    #userLogo{
      bottom:20px !important;
      left:15px !important;
      max-width:calc(100vw - 180px) !important;
      max-height:40px !important;
      width:auto !important;
      height:auto !important;
    }

    /* 어노테이션 크기 증가 */
    .annotation{font-size:14px;padding:4px 8px;min-height:32px;min-width:60px;text-align:center;}

    /* 모달 버튼 크기 증가 */
    #groupSelectBox button{padding:12px 20px;font-size:16px;min-height:48px;margin:8px auto;}

    /* 스크롤바 스타일링 */
    #groupPanel::-webkit-scrollbar{width:8px;}
    #groupPanel::-webkit-scrollbar-thumb{background:#ccc;border-radius:4px;}
    #groupPanel::-webkit-scrollbar-track{background:#f1f1f1;}
  }

  /* 터치 홀드 시각 피드백 애니메이션 */
  @keyframes pulse {
    0% {
      transform: scale(0.8);
      opacity: 0.5;
    }
    50% {
      transform: scale(1.1);
      opacity: 1;
    }
    100% {
      transform: scale(1);
      opacity: 0.9;
    }
  }
</style>
</head>
<body>
$top_logo
$user_logo

<div id="groupPanel"></div>

<div id="topButtons">
  <button id="saveGroupsBtn">Save</button>
</div>

<button id="addAnnoBtn">Add&nbsp;Annotation</button>

<div id="viewSavePanel">
  <button id="saveViewBtn">Save View</button>
  <div id="viewButtons"></div>
</div>

<div id="groupSelectModal"><div id="groupSelectBox"></div></div>

<div id="viewer"></div>

<button id="mobileToggleBtn">☰</button>

<button id="dlasHomeBtn" onclick="window.open('https://dlas.io/','_blank')">dlas.io</button>

<script>
let modelData=[ $js_models ];
let annotationList = $annos_json;
let scene,camera,renderer,controls,stlModels=[];
const groupColorMap=$js_colormap;
let fileHandle=null;
function groupKey(g){switch(g){
  case"upper_crownbridge":return["upper","crown"];
  case"upper_abutment":return["upper","abutment"];
  case"upper_scan":return["upper","scan"];
  case"lower_crownbridge":return["lower","crown"];
  case"lower_abutment":return["lower","abutment"];
  case"lower_scan":return["lower","scan"];
  case"bite":return["bite",""]; case"annotation":return["annotation",""]; default:return["etc",""];}
}
const gColor=g=>groupColorMap[g]||groupColorMap["etc"];
const fileName=location.pathname.split("/").pop()||"DLAS_STL_Viewer.html";
const safeStringify=obj=>JSON.stringify(obj).replace(/</g,"\\u003C").replace(/>/g,"\\u003E");

let savedViews=[];
function saveCurrentView(){const v={pos:camera.position.clone(),tgt:controls.target.clone()};savedViews.push(v);if(savedViews.length>5)savedViews.shift();updateViewButtons();}
function applyView(idx){if(idx<0||idx>=savedViews.length)return;const v=savedViews[idx];camera.position.copy(v.pos);controls.target.copy(v.tgt);controls.update();updateAnnotationPositions();}
function updateViewButtons(){const cont=document.getElementById("viewButtons");cont.innerHTML="";savedViews.forEach((_,i)=>{const b=document.createElement("button");b.className="viewBtn";b.textContent="V"+(i+1);b.onclick=()=>applyView(i);cont.appendChild(b);});}

function initThree(){
  const c=document.getElementById("viewer");
  scene=new THREE.Scene();scene.background=new THREE.Color(0xF5F5F5);
  camera=new THREE.PerspectiveCamera(5,window.innerWidth/window.innerHeight,10,20000);camera.position.set(0,0,1000);scene.add(camera);
  renderer=new THREE.WebGLRenderer({antialias:true});renderer.setSize(window.innerWidth,window.innerHeight);c.appendChild(renderer.domElement);
  controls=new THREE.TrackballControls(camera,renderer.domElement);
  controls.rotateSpeed=3.0;
  controls.zoomSpeed=1.2;
  controls.panSpeed=0.1;
  controls.noRotate=false;
  controls.noZoom=false;
  controls.noPan=false;
  controls.staticMoving=true;
  controls.dynamicDampingFactor=0.2;
  renderer.domElement.addEventListener('contextmenu',e=>e.preventDefault());
  scene.add(new THREE.AmbientLight(0xffffff,.2));
  [new THREE.Vector3(1,0,0),new THREE.Vector3(-1,0,0),new THREE.Vector3(0,1,0),new THREE.Vector3(0,-1,0),new THREE.Vector3(0,0,1),new THREE.Vector3(0,0,-1)]
   .forEach(d=>{const l=new THREE.DirectionalLight(0xffffff,.4);l.position.copy(d);scene.add(l);});
}
function animate(){requestAnimationFrame(animate);controls.update();renderer.render(scene,camera);updateAnnotationPositions();}

function loadAllModels(){
  modelData.forEach(md=>{
    const bin=Uint8Array.from(atob(md.b64),c=>c.charCodeAt(0));
    new THREE.GLTFLoader().parse(bin.buffer,"",gltf=>{
      const m=gltf.scene;const col=gColor(md.group);
      m.traverse(ch=>{if(ch.isMesh){ch.geometry.computeVertexNormals();ch.material=new THREE.MeshPhongMaterial({color:col,side:THREE.DoubleSide,shininess:30,specular:0x111111,opacity:1,transparent:false});}});scene.add(m);
      stlModels.push({name:md.name,object:m,group:md.group});
    });
  });
}

const ray=new THREE.Raycaster();const mouse=new THREE.Vector2();let annoMenuDiv=null;
let annotationID=annotationList.length?Math.max(...annotationList.map(a=>parseInt((a.id||"").split("_")[1]||0))):0;
function restoreAnnotations(){
  annotationList.forEach(a=>{
    if(Array.isArray(a.pos))a.pos=new THREE.Vector3(a.pos[0],a.pos[1],a.pos[2]);
    const div=document.createElement("div");div.className="annotation";div.textContent=a.text;document.body.appendChild(div);a.div=div;
    div.onclick=e=>showAnnoMenu(a,e.pageX,e.pageY);
  });
}

let collapseState={};
function captureCollapse(){document.querySelectorAll(".collapseBtn").forEach(btn=>{const tgt=btn.dataset.target;const el=document.getElementById(tgt);if(tgt&&el)collapseState[tgt]=el.style.display!=="none";});}
function restoreCollapse(){Object.entries(collapseState).forEach(([id,open])=>{const el=document.getElementById(id);const btn=document.querySelector(`.collapseBtn[data-target='${id}']`);if(el&&btn){el.style.display=open?"":"none";btn.textContent=open?"▼":"▶";}});}
function buildItems(arr){return arr.map(it=>`<div class="modelitem" style="margin-left:16px;"><span data-name="${it.name}">${it.disp}</span><button class="modelToggle" data-name="${it.name}">ON/OFF</button><input type="range" class="opacity-slider" data-name="${it.name}" min="0" max="100" value="100" title="투명도"><button class="modelEdit" data-name="${it.name}">EditGrp</button><button class="modelDelete" data-name="${it.name}">Del</button></div>`).join("");}
function buildSub(gid,label,data){if(!data.length)return"";const sid=`${gid}_${label}`;return `<div class="subgroup" style="margin-left:16px;"><button class="collapseBtn" data-target="${sid}">▶</button><span class="subName" data-group="${gid}" data-sub="${label}">${label.charAt(0).toUpperCase()+label.slice(1)}</span><button class="subgroupToggle" data-group="${gid}" data-sub="${label}">ON/OFF</button><input type="range" class="opacity-slider subgroup-opacity" data-group="${gid}" data-sub="${label}" min="0" max="100" value="100" title="투명도"><div class="children" id="${sid}" style="display:none">${buildItems(data)}</div></div>`;}
function buildGroup(key,label,obj){if(!obj.crown.length&&!obj.abutment.length&&!obj.scan.length)return"";const gid=`${key}Group`;return `<div class="group"><button class="collapseBtn" data-target="${gid}">▶</button><span class="grpName" data-group="${key}"><b>${label}</b></span><button class="groupToggle" data-group="${key}">ON/OFF</button><input type="range" class="opacity-slider group-opacity" data-group="${key}" min="0" max="100" value="100" title="투명도"><div class="children" id="${gid}" style="display:none">${buildSub(key,"crown",obj.crown)}${buildSub(key,"abutment",obj.abutment)}${buildSub(key,"scan",obj.scan)}</div></div>`;}
function buildTreeHTML(){
  const upper={crown:[],abutment:[],scan:[]},lower={crown:[],abutment:[],scan:[]},bite=[],etc=[],anno=[];
  modelData.forEach(md=>{const[k1,k2]=groupKey(md.group);const it={name:md.name,disp:md.displayName};if(k1==="upper")upper[k2].push(it);else if(k1==="lower")lower[k2].push(it);else if(k1==="bite")bite.push(it);else if(k1==="annotation")anno.push(it);else etc.push(it);});
  let rows=buildGroup("upper","Upper",upper)+buildGroup("lower","Lower",lower);
  if(bite.length){rows+=`<div class="group"><button class="collapseBtn" data-target="biteGroup">▶</button><span class="grpName" data-group="bite"><b>Bite</b></span><button class="groupToggle" data-group="bite">ON/OFF</button><input type="range" class="opacity-slider group-opacity" data-group="bite" min="0" max="100" value="100" title="투명도"><div class="children" id="biteGroup" style="display:none">${buildItems(bite)}</div></div>`;}
  if(etc.length){rows+=`<div class="group"><button class="collapseBtn" data-target="etcGroup">▶</button><span class="grpName" data-group="etc"><b>Etc</b></span><button class="groupToggle" data-group="etc">ON/OFF</button><input type="range" class="opacity-slider group-opacity" data-group="etc" min="0" max="100" value="100" title="투명도"><div class="children" id="etcGroup" style="display:none">${buildItems(etc)}</div></div>`;}
  if(annotationList.length){rows+=`<div class="group"><button class="collapseBtn" data-target="annoGroup">▶</button><span class="grpName" data-group="annotation"><b>Annotation</b></span><button class="groupToggle" data-group="annotation">ON/OFF</button><input type="range" class="opacity-slider group-opacity" data-group="annotation" min="0" max="100" value="100" title="투명도"><div class="children" id="annoGroup" style="display:none">${annotationList.map(a=>`<div class="modelitem" style="margin-left:8px;"><span>${a.text}</span><button class="annotationItem" data-id="${a.id}">Edit/Delete</button></div>`).join("")}</div></div>`;}
  return `<div class="group"><button class="collapseBtn" data-target="allChildren">▶</button><span class="allName"><b>ALL</b></span><button class="groupToggle" data-group="all">ON/OFF</button><input type="range" class="opacity-slider group-opacity" data-group="all" min="0" max="100" value="100" title="투명도"><div class="children" id="allChildren" style="display:none">${rows}</div></div>`;
}
function updateGroupPanel(){captureCollapse();document.getElementById("groupPanel").innerHTML=buildTreeHTML();restoreCollapse();bindTreeEvents();}
function bindTreeEvents(){
  document.querySelectorAll(".collapseBtn").forEach(btn=>{btn.onclick=()=>{const tgt=document.getElementById(btn.dataset.target);if(!tgt)return;const hidden=tgt.style.display==="none";tgt.style.display=hidden?"":"none";btn.textContent=hidden?"▼":"▶";collapseState[btn.dataset.target]=hidden;};});
  document.querySelectorAll(".groupToggle").forEach(btn=>{let state=true;btn.onclick=()=>{state=!state;btn.classList.toggle("off",!state);const grp=btn.dataset.group;if(grp==="all"){stlModels.forEach(it=>it.object.visible=state);annotationList.forEach(a=>a.div&&(a.div.style.display=state?"":"none"));document.querySelectorAll(".groupToggle,.subgroupToggle,.modelToggle").forEach(b=>{if(b!==btn)b.classList.toggle("off",!state);});return;}if(grp==="annotation"){annotationList.forEach(a=>a.div&&(a.div.style.display=state?"":"none"));return;}stlModels.forEach(it=>{const[k1]=groupKey(it.group);if(grp==="bite"&&k1==="bite")it.object.visible=state;else if(grp==="etc"&&k1==="etc")it.object.visible=state;else if(k1===grp)it.object.visible=state;});};});
  document.querySelectorAll(".subgroupToggle").forEach(btn=>{let state=true;btn.onclick=()=>{state=!state;btn.classList.toggle("off",!state);const grp=btn.dataset.group,sub=btn.dataset.sub;stlModels.forEach(it=>{const[k1,k2]=groupKey(it.group);if(k1===grp&&k2===sub)it.object.visible=state;});};});
  document.querySelectorAll(".modelToggle").forEach(btn=>{let state=true;btn.onclick=()=>{state=!state;btn.classList.toggle("off",!state);const nm=btn.dataset.name;stlModels.forEach(it=>{if(it.name===nm)it.object.visible=state;});};});
  document.querySelectorAll(".modelEdit").forEach(btn=>btn.onclick=()=>openGroupSelectModal(btn.dataset.name))
  document.querySelectorAll(".modelDelete").forEach(btn=>btn.onclick=()=>deleteModel(btn.dataset.name))
  document.querySelectorAll(".annotationItem").forEach(btn=>btn.onclick=e=>{const ann=annotationList.find(a=>a.id===btn.dataset.id);if(ann)showAnnoMenu(ann,e.pageX,e.pageY);});

  // 투명도 슬라이더 이벤트 (모델, 그룹, 서브그룹)
  document.querySelectorAll(".opacity-slider").forEach(slider=>{
    slider.oninput=e=>{
      const opacity=parseInt(e.target.value)/100;

      // 모델 아이템 슬라이더
      if(e.target.dataset.name){
        const name=e.target.dataset.name;
        stlModels.forEach(it=>{
          if(it.name===name){
            it.object.traverse(ch=>{
              if(ch.isMesh){
                ch.material.opacity=opacity;
                ch.material.transparent=opacity<1;
              }
            });
          }
        });
      }

      // 그룹 슬라이더
      else if(e.target.classList.contains('group-opacity')){
        const grp=e.target.dataset.group;
        if(grp==="all"){
          stlModels.forEach(it=>{
            it.object.traverse(ch=>{
              if(ch.isMesh){
                ch.material.opacity=opacity;
                ch.material.transparent=opacity<1;
              }
            });
          });
        }else{
          stlModels.forEach(it=>{
            const[k1]=groupKey(it.group);
            if((grp==="bite"&&k1==="bite")||(grp==="etc"&&k1==="etc")||(k1===grp)){
              it.object.traverse(ch=>{
                if(ch.isMesh){
                  ch.material.opacity=opacity;
                  ch.material.transparent=opacity<1;
                }
              });
            }
          });
        }
      }

      // 서브그룹 슬라이더
      else if(e.target.classList.contains('subgroup-opacity')){
        const grp=e.target.dataset.group;
        const sub=e.target.dataset.sub;
        stlModels.forEach(it=>{
          const[k1,k2]=groupKey(it.group);
          if(k1===grp&&k2===sub){
            it.object.traverse(ch=>{
              if(ch.isMesh){
                ch.material.opacity=opacity;
                ch.material.transparent=opacity<1;
              }
            });
          }
        });
      }
    };
  });
}
function setupOpacityDrag(span,getTargets){
  span.onmousedown=e=>{
    const startX=e.clientX,max=150;
    function move(ev){
      let ratio=Math.min(Math.max((ev.clientX-startX)/max,0),1);
      let op=0.2+0.8*ratio;
      stlModels.forEach(it=>{if(getTargets(it)){it.object.traverse(ch=>{if(ch.isMesh){ch.material.opacity=op;ch.material.transparent=op<1;}});}});
    }
    function up(){document.removeEventListener("mousemove",move);document.removeEventListener("mouseup",up);}
    document.addEventListener("mousemove",move);document.addEventListener("mouseup",up);
  };
  if(isMobile){
    span.ontouchstart=e=>{
      e.preventDefault();
      const startX=e.touches[0].clientX,max=150;
      function move(ev){
        let ratio=Math.min(Math.max((ev.touches[0].clientX-startX)/max,0),1);
        let op=0.2+0.8*ratio;
        stlModels.forEach(it=>{if(getTargets(it)){it.object.traverse(ch=>{if(ch.isMesh){ch.material.opacity=op;ch.material.transparent=op<1;}});}});
      }
      function up(){document.removeEventListener("touchmove",move);document.removeEventListener("touchend",up);}
      document.addEventListener("touchmove",move);document.addEventListener("touchend",up);
    };
  }
}
function bindOpacityDrag(){
  document.querySelectorAll(".modelitem span[data-name]").forEach(span=>{const name=span.dataset.name;setupOpacityDrag(span,it=>it.name===name);});
  document.querySelectorAll(".grpName").forEach(span=>{const grp=span.dataset.group;setupOpacityDrag(span,it=>{const[k1]=groupKey(it.group);return(grp==="etc"&&k1==="etc")||(grp==="bite"&&k1==="bite")||(grp==="annotation"&&k1==="annotation")||k1===grp;});});
  document.querySelectorAll(".subName").forEach(span=>{const grp=span.dataset.group,sub=span.dataset.sub;setupOpacityDrag(span,it=>{const[k1,k2]=groupKey(it.group);return k1===grp&&k2===sub;});});
  const allSpan=document.querySelector(".allName");if(allSpan)setupOpacityDrag(allSpan,()=>true);
}
function openGroupSelectModal(name){
  const md=modelData.find(m=>m.name===name);if(!md)return;
  const modal=document.getElementById("groupSelectModal"),box=document.getElementById("groupSelectBox");
  box.innerHTML="<h3 style='margin-top:0'>Select Group</h3>";
  [["upper_crownbridge","Upper Crown/Bridge"],["upper_abutment","Upper Abutment"],["upper_scan","Upper Scan"],["lower_crownbridge","Lower Crown/Bridge"],["lower_abutment","Lower Abutment"],["lower_scan","Lower Scan"],["bite","Bite"],["etc","Etc"],["annotation","Annotation"]].forEach(([gid,label])=>{const b=document.createElement("button");b.textContent=label;b.onclick=()=>{if(md.group!==gid){md.group=gid;recolor(gid);updateGroupPanel();}modal.style.display="none";};box.appendChild(b);});
  const cancel=document.createElement("button");cancel.textContent="Cancel";cancel.className="cancelBtn";cancel.onclick=()=>modal.style.display="none";box.appendChild(cancel);modal.style.display="flex";
  function recolor(g){stlModels.forEach(it=>{if(it.name===md.name){it.group=g;it.object.traverse(ch=>{if(ch.isMesh)ch.material.color.setHex(gColor(g));});}});}
}
function deleteModel(name){if(!confirm("Delete this model?"))return;const idx=modelData.findIndex(m=>m.name===name);if(idx===-1)return;modelData.splice(idx,1);const sidx=stlModels.findIndex(m=>m.name===name);if(sidx>=0){scene.remove(stlModels[sidx].object);stlModels.splice(sidx,1);}updateGroupPanel();}

async function saveHTML(){
  document.querySelectorAll('.annotation').forEach(el=>el.remove());
  const mdlPlain=modelData.map(({name,b64,group,displayName})=>({name,b64,group,displayName}));
  const annPlain=annotationList.map(o=>({id:o.id,text:o.text,pos:[o.pos.x,o.pos.y,o.pos.z]}));
  let html=_BASE_HTML.replace(/let\\s+modelData\\s*=\\s*\\[[\\s\\S]*?\\];/,'let modelData = '+safeStringify(mdlPlain)+';').replace(/let\\s+annotationList\\s*=\\s*[\\s\\S]*?;/,'let annotationList = '+safeStringify(annPlain)+';');
  const blob=new Blob([html],{type:'text/html'});
  if(window.showSaveFilePicker){
    try{
      if(!fileHandle){
        const opts={suggestedName:fileName,types:[{description:'HTML Files',accept:{'text/html':['.html']}}]};
        fileHandle=await window.showSaveFilePicker(opts);
      }
      const w=await fileHandle.createWritable();await w.write(blob);await w.close();alert('Saved.');return;
    }catch(e){console.warn('Save failed / cancelled:',e);}
  }
  let n=prompt("Save as file name:",fileName)||fileName;if(!n.toLowerCase().endsWith(".html"))n+=".html";
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=n;a.style.display="none";document.body.appendChild(a);a.click();URL.revokeObjectURL(a.href);document.body.removeChild(a);
}

function toggleAddAnno(){document.getElementById("addAnnoBtn").onclick=e=>e.target.classList.toggle("active");}
function onClickViewer(e){const btn=document.getElementById("addAnnoBtn");if(!btn.classList.contains("active"))return;const r=renderer.domElement.getBoundingClientRect();mouse.x=((e.clientX-r.left)/r.width)*2-1;mouse.y=-((e.clientY-r.top)/r.height)*2+1;ray.setFromCamera(mouse,camera);const hits=ray.intersectObjects(scene.children,true);if(!hits.length)return;const pos=hits[0].point.clone();const txt=prompt("Annotation text:");if(!txt)return;const div=document.createElement("div");div.className="annotation";div.textContent=txt;document.body.appendChild(div);const id="anno_"+(++annotationID);const obj={id:id,text:txt,pos:pos,div:div};annotationList.push(obj);div.onclick=ev=>showAnnoMenu(obj,ev.pageX,ev.pageY);updateGroupPanel();btn.classList.remove("active");updateAnnotationPositions();}
function removeAnnoById(id){const idx=annotationList.findIndex(a=>a.id===id);if(idx===-1)return;const ann=annotationList.splice(idx,1)[0];ann.div.remove();updateGroupPanel();}
function showAnnoMenu(ann,x,y){closeAnnoMenu();annoMenuDiv=document.createElement("div");annoMenuDiv.className="annoMenu";annoMenuDiv.style.left=x+"px";annoMenuDiv.style.top=y+"px";const bEdit=document.createElement("button");bEdit.textContent="Edit";const bDel=document.createElement("button");bDel.textContent="Delete";bEdit.onclick=()=>{const nv=prompt("Edit annotation:",ann.text);if(!nv)return;ann.text=nv;ann.div.textContent=nv;updateGroupPanel();closeAnnoMenu();};bDel.onclick=()=>{removeAnnoById(ann.id);closeAnnoMenu();};annoMenuDiv.appendChild(bEdit);annoMenuDiv.appendChild(bDel);document.body.appendChild(annoMenuDiv);}
function closeAnnoMenu(){if(annoMenuDiv){annoMenuDiv.remove();annoMenuDiv=null;}}
document.addEventListener("click",e=>{if(annoMenuDiv&&!annoMenuDiv.contains(e.target)&&!e.target.classList.contains("annotation"))closeAnnoMenu();});
function updateAnnotationPositions(){annotationList.forEach(a=>{if(!a.pos||!a.div)return;const v=a.pos.clone().project(camera);a.div.style.left=((v.x*0.5+0.5)*window.innerWidth)+"px";a.div.style.top=((-v.y*0.5+0.5)*window.innerHeight)+"px";});}

function focusToPoint(cx,cy){
  const r=renderer.domElement.getBoundingClientRect();
  mouse.x=((cx-r.left)/r.width)*2-1;
  mouse.y=-((cy-r.top)/r.height)*2+1;
  ray.setFromCamera(mouse,camera);
  const hits=ray.intersectObjects(scene.children,true);
  if(!hits.length)return;

  const targetPoint=hits[0].point.clone();
  const offset=new THREE.Vector3().subVectors(camera.position,controls.target);

  // 부드러운 애니메이션을 위한 시작/목표 위치
  const startTarget=controls.target.clone();
  const endTarget=targetPoint.clone();
  const startPos=camera.position.clone();
  const endPos=endTarget.clone().add(offset);

  // 애니메이션 변수
  let animProgress=0;
  const animDuration=300; // 300ms 애니메이션
  const startTime=performance.now();

  function animate(){
    const elapsed=performance.now()-startTime;
    animProgress=Math.min(elapsed/animDuration,1);

    // easeOutCubic 이징 함수 (부드러운 감속)
    const eased=1-Math.pow(1-animProgress,3);

    // lerp (선형 보간)
    controls.target.lerpVectors(startTarget,endTarget,eased);
    camera.position.lerpVectors(startPos,endPos,eased);
    controls.update();
    updateAnnotationPositions();

    if(animProgress<1){
      requestAnimationFrame(animate);
    }
  }

  animate();
}
function enableFocusEvents(){
  const dom=renderer.domElement;

  // 마우스 중간 버튼으로 회전 중심 설정
  dom.addEventListener("mousedown",e=>{
    if(e.button===1){
      e.preventDefault();
      focusToPoint(e.clientX,e.clientY);
    }
  },false);

  // 터치 홀드 (0.2초)로 회전 중심 설정 + 시각적 피드백
  let touchTimer=null;
  let touchIndicator=null;

  dom.addEventListener("touchstart",e=>{
    if(e.touches.length===1){
      const t=e.touches[0];

      // 시각적 피드백: 홀드 표시 원
      touchIndicator=document.createElement('div');
      touchIndicator.style.cssText=`
        position:fixed;
        left:${t.clientX-20}px;
        top:${t.clientY-20}px;
        width:40px;
        height:40px;
        border:3px solid #2196F3;
        border-radius:50%;
        pointer-events:none;
        z-index:9999;
        animation:pulse 0.2s ease-out;
      `;
      document.body.appendChild(touchIndicator);

      touchTimer=setTimeout(()=>{
        focusToPoint(t.clientX,t.clientY);
        if(touchIndicator){
          touchIndicator.style.borderColor='#4CAF50';
          touchIndicator.style.transform='scale(1.3)';
          setTimeout(()=>{
            if(touchIndicator&&touchIndicator.parentNode){
              document.body.removeChild(touchIndicator);
            }
            touchIndicator=null;
          },300);
        }
      },200);
    }
  },false);

  ["touchend","touchcancel","touchmove"].forEach(ev=>dom.addEventListener(ev,()=>{
    if(touchTimer){
      clearTimeout(touchTimer);
      touchTimer=null;
    }
    if(touchIndicator&&touchIndicator.parentNode){
      document.body.removeChild(touchIndicator);
      touchIndicator=null;
    }
  },false));
}

function initMobileUI(){
  console.log("initMobileUI 시작");
  const panel=document.getElementById("groupPanel");
  const toggleBtn=document.getElementById("mobileToggleBtn");
  console.log("toggleBtn:", toggleBtn);
  console.log("panel:", panel);

  if(!toggleBtn){
    console.log("toggleBtn이 없어서 종료");
    return;
  }
  if(!panel){
    console.log("panel이 없어서 종료");
    return;
  }

  let isPanelOpen=false;
  console.log("이벤트 리스너 설정 중...");

  function closePanel(){
    console.log("패널 닫힘");
    isPanelOpen=false;
    panel.classList.remove("mobile-open");
    toggleBtn.textContent="☰";
    toggleBtn.style.background="#198754";
  }

  function openPanel(){
    console.log("패널 열림");
    isPanelOpen=true;
    panel.classList.add("mobile-open");
    toggleBtn.textContent="✕";
    toggleBtn.style.background="#dc3545";
  }

  toggleBtn.onclick=()=>{
    console.log("토글 버튼 클릭, isPanelOpen:", isPanelOpen);
    if(isPanelOpen){
      closePanel();
    }else{
      openPanel();
    }
  };

  // 화면 클릭 시 패널 닫힘 (인터랙티브 요소와 콘텐츠 영역만 제외)
  const handleScreenClick=(e)=>{
    if(!isPanelOpen)return;

    // 토글 버튼 클릭은 제외
    if(toggleBtn.contains(e.target)||e.target===toggleBtn)return;

    const target=e.target;

    // 인터랙티브 요소들은 보호 (클릭해도 패널 안 닫힘)
    // 1. 버튼, 입력 요소
    if(target.tagName==='BUTTON'||target.tagName==='INPUT'||target.tagName==='SELECT'){
      return;
    }

    // 2. SPAN 요소 (모델명, 그룹명 - opacity drag 기능)
    if(target.tagName==='SPAN'&&(target.hasAttribute('data-name')||target.hasAttribute('data-group')||
       target.classList.contains('grpName')||target.classList.contains('subName')||
       target.classList.contains('allName'))){
      return;
    }

    // 3. B 태그 (볼드 텍스트)
    if(target.tagName==='B'){
      return;
    }

    // 4. 버튼/입력의 부모 요소
    if(target.closest('button:not(#mobileToggleBtn)')||target.closest('input')||target.closest('select')){
      return;
    }

    // 5. 그룹/서브그룹/모델 아이템 박스 영역 보호 (배경 박스 클릭 시에도 유지)
    if(target.classList.contains('group')||target.classList.contains('subgroup')||
       target.classList.contains('modelitem')||target.classList.contains('children')||
       target.closest('.group')||target.closest('.subgroup')||target.closest('.modelitem')){
      return;
    }

    // 나머지는 모두 패널 닫기 (패널 외곽 배경, 3D 뷰어 등)
    console.log("빈 영역 클릭 → 패널 닫기");
    closePanel();
  };

  // 터치와 클릭 모두 지원
  document.body.addEventListener("touchstart",handleScreenClick,true);
  document.body.addEventListener("click",handleScreenClick,true);
  console.log("3D 뷰어 클릭 이벤트 등록 완료");
  console.log("initMobileUI 완료!");
}

window.onload=()=>{initThree();loadAllModels();restoreAnnotations();updateGroupPanel();toggleAddAnno();animate();document.getElementById("saveGroupsBtn").onclick=saveHTML;document.getElementById("saveViewBtn").onclick=saveCurrentView;renderer.domElement.addEventListener("click",onClickViewer,false);enableFocusEvents();updateViewButtons();initMobileUI();};
window.onresize=()=>{camera.aspect=window.innerWidth/window.innerHeight;camera.updateProjectionMatrix();renderer.setSize(window.innerWidth,window.innerHeight);};
</script>
</body>
</html>""")

    return html_tpl.safe_substitute(
        js_models=js_models,
        annos_json=annos_json,
        js_colormap=js_colormap,
        top_logo=top_logo_html,
        user_logo=user_logo_html
    )

# ==============================================================================
# 공통: 프리/안티 스캔 판별
# ==============================================================================
def _is_prep_scan(fname: str) -> bool:
    l = fname.lower()
    return ("preparationscan" in l or ("prep" in l and "scan" in l)) and "prepreparation" not in l

def _is_ant_scan(fname: str) -> bool:
    l = fname.lower()
    return "antagonist" in l or (l.startswith("ant") and "scan" in l) or "opposing" in l

# ==============================================================================
# Worker Process for HTML Conversion (C++ crash protection)
# ==============================================================================
def _run_html_worker_process(result_queue, work_folder_str, stl_paths_list, html_path_str,
                              mode_str, user_logo_path_str, skip_processed):
    """
    별도 프로세스에서 HTML 변환 작업 실행
    C++ 크래시가 발생해도 메인 프로세스는 영향받지 않음
    """
    try:
        # skip_processed 체크
        if skip_processed and is_folder_processed(work_folder_str):
            result_queue.put(("skipped", "already processed"))
            return

        # mode 감지
        mode = detect_mode(work_folder_str)
        stl_paths = find_stl_files(work_folder_str, log_callback=None)

        if not stl_paths:
            result_queue.put(("skipped", "no STL files"))
            return

        # HTML 변환 실행
        convert_stls_to_html(
            stl_paths, html_path_str, work_folder_str, mode,
            log_callback=None,
            user_logo_path=user_logo_path_str,
            progress_callback=None
        )

        # 마커 파일 생성
        create_folder_marker(work_folder_str)
        result_queue.put(("success", os.path.basename(html_path_str)))

    except BaseException as e:
        result_queue.put(("error", str(e)))

# ==============================================================================
# 변환 파이프라인 (모드별 공통)
# ==============================================================================
def convert_stls_to_html(stl_paths: list[str], save_html_path: str, folder_for_mapping: str,
                         work_mode: str,
                         log_callback=None, user_logo_path: str | None = None,
                         group_override: dict[str, str] | None = None,
                         progress_callback=None) -> None:
    """
    work_mode: '3shape' | 'exo'
    folder_for_mapping: 그룹/표시 파싱 기준 폴더
    """
    if not stl_paths:
        log_callback and log_callback("[WARN] STL 파일이 없습니다.")
        return

    temp_reduce_dir = tempfile.mkdtemp(prefix="dlas_reduce_")
    temp_xfm_dir    = tempfile.mkdtemp(prefix="dlas_xfm_")
    model_infos: list[dict[str, str]] = []
    parsed_excel_path = None

    try:
        # ----- 그룹/표시 맵 준비 -----
        if group_override:
            group_map = group_override
            display_map = {}
        else:
            if work_mode == "3shape":
                try:
                    df_an = analyze_folder_3shape(Path(folder_for_mapping))
                    parsed_excel_path = str(Path(folder_for_mapping) / "parsed_3shape.xlsx")
                    export_to_excel(df_an, Path(folder_for_mapping) / "parsed_3shape")
                    log_callback and log_callback("[INFO] parsed_3shape.xlsx 생성 완료.")
                except Exception as e:
                    log_callback and log_callback(f"[WARN] Excel 생성 스킵: {e}")
                group_map = parse_3ox_for_groups(folder_for_mapping)
                display_map = parse_3ox_for_display(folder_for_mapping)
            else:  # EXO
                group_map = parse_exo_for_groups(folder_for_mapping)
                display_map = parse_exo_for_display(folder_for_mapping)

        # constructionInfo / modelInfo root (EXO 변환행렬용)
        ci_file, mi_file = _find_exo_files(folder_for_mapping)
        exo_ci_root = None
        exo_mi_root = None
        if work_mode == "exo":
            if ci_file:
                try:
                    exo_ci_root = ET.parse(ci_file).getroot()
                except Exception as e:
                    log_callback and log_callback(f"[WARN] EXO constructionInfo 파싱 실패: {e}")
            if mi_file:
                try:
                    exo_mi_root = ET.parse(mi_file).getroot()
                except Exception as e:
                    log_callback and log_callback(f"[WARN] EXO modelInfo 파싱 실패: {e}")

        # ----- STL 별 처리 (감소 → glb) -----
        u_crown, l_crown = [], []
        u_prep,  l_prep  = [], []
        u_ant,   l_ant   = [], []
        u_scan,  l_scan  = [], []

        total_cnt = len([p for p in stl_paths if p.lower().endswith((".stl", ".ply"))])
        done_cnt = 0

        for fp in stl_paths:
            if not (os.path.isfile(fp) and fp.lower().endswith((".stl", ".ply"))):
                continue
            try:
                src_for_reduce = fp
                # EXO 모드에서 행렬 있으면 좌표 정렬 (원본 이름 유지, 별도 temp 폴더 사용)
                if work_mode == "exo" and (exo_ci_root is not None or exo_mi_root is not None):
                    src_for_reduce = exo_transform_if_possible(fp, exo_ci_root, exo_mi_root, temp_xfm_dir)

                log_callback and log_callback(f"[INFO] Reducing: {os.path.basename(src_for_reduce)}")
                reduced_fp = reduce_stl_size(src_for_reduce, temp_reduce_dir)
                name = os.path.basename(reduced_fp)
                grp = group_map.get(name, "etc")
                disp = display_map.get(name, os.path.splitext(name)[0])

                # BITE 후보 수집
                if grp == "upper_crownbridge":
                    u_crown.append(reduced_fp)
                elif grp == "lower_crownbridge":
                    l_crown.append(reduced_fp)
                elif grp == "upper_scan":
                    if _is_prep_scan(name): u_prep.append(reduced_fp)
                    elif _is_ant_scan(name): u_ant.append(reduced_fp)
                    elif work_mode == "exo": u_scan.append(reduced_fp)
                elif grp == "lower_scan":
                    if _is_prep_scan(name): l_prep.append(reduced_fp)
                    elif _is_ant_scan(name): l_ant.append(reduced_fp)
                    elif work_mode == "exo": l_scan.append(reduced_fp)

                model_infos.append({
                    "name": name,
                    "b64": convert_stl_to_gltf(reduced_fp),
                    "group": grp,
                    "displayName": disp
                })
                log_callback and log_callback(f"[OK] {name} → {grp}")
            except Exception as e:
                log_callback and log_callback(f"[ERR] {fp}: {e}")
            finally:
                done_cnt += 1
                log_callback and log_callback(f"[PROGRESS] {done_cnt}/{total_cnt}")
                # 진행률 콜백 호출 (파일 단위로 세밀하게)
                if progress_callback:
                    progress = (done_cnt / total_cnt) * 100
                    progress_callback(progress, f"파일 변환 중... ({done_cnt}/{total_cnt})")

        # ----- BITE 생성 (있을 때만) -----
        bite_fp = None
        upper_candidates = u_crown + u_prep + (u_scan if work_mode == "exo" else [])
        lower_candidates = l_crown + l_prep + (l_scan if work_mode == "exo" else [])

        if upper_candidates and lower_candidates:
            log_callback and log_callback("[INFO] Generating BITE (both‑side)…")
            bite_fp = generate_bite_stl(upper_candidates, lower_candidates, temp_reduce_dir)
        elif upper_candidates:
            log_callback and log_callback("[INFO] Generating BITE (upper‑only)…")
            bite_fp = generate_bite_stl(upper_candidates, l_ant, temp_reduce_dir)
        elif lower_candidates:
            log_callback and log_callback("[INFO] Generating BITE (lower‑only)…")
            bite_fp = generate_bite_stl(lower_candidates, u_ant, temp_reduce_dir)

        if bite_fp:
            model_infos.append({
                "name": os.path.basename(bite_fp),
                "b64": convert_stl_to_gltf(bite_fp),
                "group": "bite",
                "displayName": "BITE"
            })
            log_callback and log_callback(f"[OK] BITE STL saved: {os.path.basename(bite_fp)}")
        else:
            log_callback and log_callback("[INFO] No BITE generated (insufficient data or no intersection).")

        # ----- HTML 저장 -----
        user_logo_b64 = encode_image_b64(user_logo_path) if user_logo_path else None
        ann_plain = []
        with open(save_html_path, "w", encoding="utf-8") as f:
            f.write(generate_html(model_infos, json.dumps(ann_plain), user_logo_b64))
        log_callback and log_callback(f"[SAVE] {save_html_path}")

    finally:
        if parsed_excel_path and os.path.exists(parsed_excel_path):
            try:
                os.remove(parsed_excel_path)
                log_callback and log_callback(f"[INFO] parsed_3shape.xlsx 삭제 완료")
            except Exception as e:
                log_callback and log_callback(f"[WARN] parsed_3shape.xlsx 삭제 실패: {e}")
        shutil.rmtree(temp_reduce_dir, ignore_errors=True)
        shutil.rmtree(temp_xfm_dir,    ignore_errors=True)
        log_callback and log_callback(f"[INFO] Removed temp dirs.")

# ==============================================================================
# GUI – 공용 요소
# ==============================================================================
def is_folder_processed(folder_path: str) -> bool:
    return os.path.exists(os.path.join(folder_path, "folder.processed_html_converter"))
def create_folder_marker(folder_path: str) -> None:
    try:
        with open(os.path.join(folder_path, "folder.processed_html_converter"), "w") as f:
            f.write("processed by HTML Converter")
    except Exception as e:
        print(f"[WARN] Cannot create marker in {folder_path}: {e}")

def find_matching_folders(base_path: str,
                          time_limit_hours: int | None = None,
                          keyword: str | None = None) -> list[str]:
    matching: list[str] = []
    now = time.time()
    def check(p: str) -> None:
        try:
            if time_limit_hours is not None and (now - os.path.getmtime(p)) / 3600 > time_limit_hours:
                return
        except OSError:
            return
        if keyword and keyword.lower() not in os.path.basename(p).lower():
            return
        matching.append(p)
    check(base_path)
    for root, dirs, _ in os.walk(base_path):
        for d in dirs:
            check(os.path.join(root, d))
    return matching

def expand_candidates_with_zips(folder: str) -> list[str]:
    cands = [folder]
    extracted = _extract_zips_to_temp(folder)
    cands.extend(extracted)
    return cands

def extract_scan_files_from_constructioninfo(ci_path: str) -> list[str]:
    """
    constructionInfo에서 사용된 스캔 파일명 추출
    Returns: 스캔 파일명 리스트 (예: ['2025-07-24-00000-000-upperjaw.ply', ...])
    """
    scan_files = []
    try:
        tree = ET.parse(ci_path)
        root = tree.getroot()

        # ScanFiles 섹션에서 파일명 추출
        scan_files_elem = root.find("ScanFiles")
        if scan_files_elem is not None:
            for scan_file in scan_files_elem.findall("ScanFile"):
                filename_elem = scan_file.find("FileName")
                if filename_elem is not None and filename_elem.text:
                    scan_files.append(filename_elem.text.strip())

        # ToothScanFileName도 확인
        for tooth in root.findall(".//Tooth"):
            tooth_scan = tooth.find("ToothScanFileName")
            if tooth_scan is not None and tooth_scan.text:
                fname = tooth_scan.text.strip()
                if fname and fname not in scan_files:
                    scan_files.append(fname)

    except Exception as e:
        print(f"[WARN] constructionInfo 스캔 파일 추출 실패: {e}")

    return scan_files

def search_file_globally(filename: str, search_roots: list[str] = None, log_callback=None) -> str | None:
    """
    제한적 파일 검색 (속도 최적화)
    Args:
        filename: 검색할 파일명
        search_roots: 검색할 루트 경로들 (None이면 제한된 경로만 검색)
        log_callback: 로그 출력 함수
    Returns: 찾은 파일의 전체 경로 또는 None
    """
    import glob

    if log_callback:
        log_callback(f"[INFO] '{filename}' 검색 중...")

    # 기본 검색 경로 설정 (빠른 검색을 위해 제한)
    if search_roots is None:
        search_roots = [
            os.path.join(os.path.expanduser("~"), "Documents"),  # 사용자 문서
            os.path.join(os.path.expanduser("~"), "Desktop"),    # 사용자 바탕화면
            "C:\\exocad-DentalCAD3.0-2021-03-25",  # exocad 기본 경로
            "C:\\exocad",  # exocad 대체 경로
        ]

    MAX_DEPTH = 4  # 최대 검색 깊이 제한

    # 각 루트에서 검색
    for root_path in search_roots:
        if not os.path.exists(root_path):
            continue

        if log_callback:
            log_callback(f"[INFO] {root_path}에서 검색 중...")

        try:
            # os.walk로 제한적 재귀 검색
            for dirpath, dirnames, filenames in os.walk(root_path):
                # 검색 깊이 제한
                depth = dirpath[len(root_path):].count(os.sep)
                if depth >= MAX_DEPTH:
                    dirnames[:] = []  # 더 깊이 들어가지 않음
                    continue

                # 시스템 폴더 및 큰 폴더는 스킵
                dirnames[:] = [d for d in dirnames if d not in
                              ['Windows', 'Program Files', 'Program Files (x86)',
                               '$Recycle.Bin', 'System Volume Information',
                               'ProgramData', 'node_modules', '.git', '__pycache__']]

                if filename in filenames:
                    found_path = os.path.join(dirpath, filename)
                    if log_callback:
                        log_callback(f"[OK] 파일 발견: {found_path}")
                    return found_path

                # .ply 파일의 경우 대소문자 구분 없이 검색
                if filename.lower().endswith('.ply'):
                    for f in filenames:
                        if f.lower() == filename.lower():
                            found_path = os.path.join(dirpath, f)
                            if log_callback:
                                log_callback(f"[OK] 파일 발견: {found_path}")
                            return found_path

        except (PermissionError, OSError) as e:
            # 접근 권한 없는 폴더는 스킵
            continue

    if log_callback:
        log_callback(f"[WARN] '{filename}' 파일을 찾을 수 없습니다.")
    return None

def find_stl_files(folder: str, log_callback=None) -> list[str]:
    """
    폴더에서 STL/PLY 파일 찾기 + constructionInfo 기반 자동 검색
    """
    stls = []

    # 1단계: 폴더 내 모든 STL/PLY 파일 수집
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith((".stl", ".ply")):
                stls.append(os.path.join(root, f))

    # 2단계: constructionInfo에서 스캔 파일 확인
    ci_path = None
    for f in os.listdir(folder):
        if f.lower().endswith(".constructioninfo") or (f.lower().endswith(".xml") and "constructioninfo" in f.lower()):
            ci_path = os.path.join(folder, f)
            break

    if ci_path and os.path.isfile(ci_path):
        if log_callback:
            log_callback(f"[INFO] constructionInfo 발견: {os.path.basename(ci_path)}")

        scan_files = extract_scan_files_from_constructioninfo(ci_path)

        if scan_files and log_callback:
            log_callback(f"[INFO] constructionInfo에서 {len(scan_files)}개 스캔 파일 발견")

        # 3단계: 스캔 파일이 폴더에 없으면 전체 검색
        for scan_file in scan_files:
            # 파일이 이미 stls에 있는지 확인
            found_locally = False
            for existing_stl in stls:
                if os.path.basename(existing_stl).lower() == scan_file.lower():
                    found_locally = True
                    break

            if not found_locally:
                if log_callback:
                    log_callback(f"[WARN] 스캔 파일 누락: {scan_file}")
                    log_callback(f"[INFO] 제한적 검색 시작 (속도 최적화)...")

                # 제한적 검색 실행 (최적화됨)
                found_path = search_file_globally(scan_file, log_callback=log_callback)

                if found_path:
                    stls.append(found_path)
                    if log_callback:
                        log_callback(f"[OK] 스캔 파일 추가: {found_path}")
                else:
                    if log_callback:
                        log_callback(f"[WARN] 스캔 파일을 찾을 수 없음 (누락 파일 무시): {scan_file}")

    return stls

# ==============================================================================
# Manual 그룹 선택 대화상자
# ==============================================================================
_GROUP_LIST = [
    "upper_crownbridge", "upper_abutment", "upper_scan",
    "lower_crownbridge", "lower_abutment", "lower_scan",
    "bite", "etc"
]
class ManualGroupDialog(QDialog):
    def __init__(self, stl_files: list[str], default_map: dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("STL Group Mapping")
        self.resize(560, 480)

        vbox = QVBoxLayout(self)
        tbl = QTableWidget(len(stl_files), 2, self)
        tbl.setHorizontalHeaderLabels(["STL Filename", "Group"])
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.verticalHeader().setVisible(False)

        for row, fn in enumerate(stl_files):
            tbl.setItem(row, 0, QTableWidgetItem(fn))
            cb = QComboBox()
            cb.addItems(_GROUP_LIST)
            cb.setCurrentText(default_map.get(fn, "etc"))
            tbl.setCellWidget(row, 1, cb)

        vbox.addWidget(tbl)
        self.tbl = tbl

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("OK");     btn_cancel = QPushButton("Cancel")
        btn_ok.clicked.connect(self.accept); btn_cancel.clicked.connect(self.reject)
        btn_box.addStretch(); btn_box.addWidget(btn_ok); btn_box.addWidget(btn_cancel)
        vbox.addLayout(btn_box)

    def mapping(self) -> dict[str, str]:
        mp: dict[str, str] = {}
        for row in range(self.tbl.rowCount()):
            fn = self.tbl.item(row, 0).text()
            grp = self.tbl.cellWidget(row, 1).currentText()
            mp[fn] = grp
        return mp

# ==============================================================================
# Heartbeat (옵션) – 동일 세션 보호
# ==============================================================================
heartbeat_token = None
heartbeat_session_id = None
heartbeat_timer = None
def parse_token_and_sid() -> None:
    global heartbeat_token, heartbeat_session_id
    for arg in sys.argv:
        if arg.startswith("--token="):
            heartbeat_token = arg.split("=", 1)[1]
        elif arg.startswith("--sid="):
            heartbeat_session_id = arg.split("=", 1)[1]
def send_heartbeat() -> None:
    try:
        import urllib.request
        url = "https://license-server-697p.onrender.com/auth/heartbeat"
        hdr = {"Authorization": f"Bearer {heartbeat_token}", "Content-Type": "application/json"}
        req = urllib.request.Request(url, headers=hdr, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            if json.loads(res.read() or "{}").get("status") != "OK":
                raise RuntimeError("Heartbeat rejected")
    except Exception as e:
        print("[Heartbeat] Failed:", e)
        force_logout()
def force_logout() -> None:
    QMessageBox.critical(None, "Logged out", "다른 PC에서 동일 계정으로 로그인되어 세션이 종료되었습니다.")
    sys.exit(0)
def start_heartbeat() -> None:
    global heartbeat_timer
    heartbeat_timer = QTimer(); heartbeat_timer.timeout.connect(send_heartbeat); heartbeat_timer.start(2 * 60 * 1000)

# ==============================================================================
# GUI
# ==============================================================================
GUI_LEFTBOTTOM_LOGO = resource_path("logo.png")
WINDOW_ICON         = resource_path("logo.ico")
TITLE_IMAGE         = resource_path("fast_html_viewer_converter.png")

class NoWheelComboBox(QComboBox):
    """휠 스크롤로 값이 변경되지 않는 ComboBox"""
    def wheelEvent(self, event):
        event.ignore()

class STLViewerGUI(QMainWindow):
    update_progress_signal = Signal(int, str)

    def __init__(self):
        super().__init__()
        self.folder_path: str | None = None
        self.output_folder: str | None = None
        self.user_logo_path: str | None = None
        self.worker_thread: threading.Thread | None = None
        self.stop_requested = False
        self.settings = QSettings("DLAS", "fast_html_viewer_converter")
        self.update_progress_signal.connect(self.on_progress_update_slot)

        # 깜빡임 효과를 위한 타이머
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self._blink_status_label)
        self.blink_state = False

        self.load_config()
        self.init_ui()

    def load_config(self) -> None:
        if os.path.exists(CONFIG_PATH):
            try:
                cfg = json.load(open(CONFIG_PATH, "r", encoding="utf-8"))
                self.user_logo_path = cfg.get("user_logo_path")
            except Exception:
                self.user_logo_path = None

    def save_config(self) -> None:
        try:
            json.dump({"user_logo_path": self.user_logo_path or ""}, open(CONFIG_PATH, "w", encoding="utf-8"))
        except Exception:
            pass

    def create_card(self):
        """Create card-style frame"""
        card = QFrame()
        card.setStyleSheet(Style.card_style())
        return card

    def init_ui(self) -> None:
        self.setWindowTitle("DLAS HTML 뷰어 변환기")
        self.setGeometry(100, 100, 620, 800)
        if os.path.exists(WINDOW_ICON):
            self.setWindowIcon(QIcon(WINDOW_ICON))

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {Style.BG_MAIN};
                font-family: 'Malgun Gothic', '맑은 고딕', sans-serif;
            }}
        """)

        # Scroll area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet(Style.scrollbar())
        self.setCentralWidget(scroll_area)

        main_widget = QWidget()
        scroll_area.setWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Header (back button)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)
        header_layout.addStretch()

        back_btn = QPushButton("← 모듈 선택")
        back_btn.setFixedSize(120, 36)
        back_btn.setStyleSheet(Style.secondary_button())
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.clicked.connect(self.return_to_module_selection)
        header_layout.addWidget(back_btn)

        main_layout.addLayout(header_layout)

        # Title (module image)
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)

        if os.path.exists(TITLE_IMAGE):
            title_layout.addStretch()
            icon_label = QLabel()
            pixmap = QPixmap(TITLE_IMAGE)
            scaled = pixmap.scaledToHeight(45, Qt.SmoothTransformation)
            icon_label.setPixmap(scaled)
            title_layout.addWidget(icon_label)
            title_layout.addStretch()
        else:
            title_layout.addStretch()

        main_layout.addLayout(title_layout)

        # Description
        desc_label = QLabel("HTML변환 모듈")
        desc_label.setStyleSheet(f"font-size: 13px; color: {Style.TEXT_SECONDARY};")
        desc_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc_label)

        # Mode selection card
        mode_card = self.create_card()
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setSpacing(8)

        mode_label = QLabel("모드 선택")
        mode_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Style.TEXT_PRIMARY};")
        mode_layout.addWidget(mode_label)

        self.mode_combo = NoWheelComboBox()
        self.mode_combo.addItems(["자동", "수동"])
        self.mode_combo.setStyleSheet(Style.combobox())
        mode_layout.addWidget(self.mode_combo)

        main_layout.addWidget(mode_card)

        # Folder selection card
        folder_card = self.create_card()
        folder_layout = QVBoxLayout(folder_card)
        folder_layout.setSpacing(8)

        folder_label = QLabel("작업 폴더")
        folder_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Style.TEXT_PRIMARY};")
        folder_layout.addWidget(folder_label)

        folder_row = QHBoxLayout()
        self.folder_display = QLabel("폴더를 선택하세요")
        self.folder_display.setMinimumHeight(40)
        self.folder_display.setStyleSheet(f"""
            QLabel {{
                background-color: {Style.BG_CARD};
                padding: 8px;
                border-radius: 6px;
                color: {Style.TEXT_SECONDARY};
                font-size: 11px;
            }}
        """)
        self.folder_display.setWordWrap(True)
        folder_row.addWidget(self.folder_display, 1)

        folder_btn = QPushButton("폴더 선택")
        folder_btn.setFixedSize(100, 32)
        folder_btn.setStyleSheet(Style.small_button())
        folder_btn.setCursor(QCursor(Qt.PointingHandCursor))
        folder_btn.clicked.connect(self.select_folder)
        folder_row.addWidget(folder_btn)

        folder_layout.addLayout(folder_row)

        main_layout.addWidget(folder_card)

        # Time/Keyword filter card
        filter_card = self.create_card()
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setSpacing(8)

        filter_label = QLabel("검색 필터")
        filter_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Style.TEXT_PRIMARY};")
        filter_layout.addWidget(filter_label)

        # Time Range
        time_row = QHBoxLayout()
        time_lbl = QLabel("시간 범위:")
        time_lbl.setMinimumWidth(100)
        time_row.addWidget(time_lbl)

        self.time_combo = NoWheelComboBox()
        self.time_combo.addItems(["제한없음"]+[f"{i}시간 이내" for i in range(1,49)])
        self.time_combo.setStyleSheet(Style.combobox())
        time_row.addWidget(self.time_combo, 1)

        filter_layout.addLayout(time_row)

        # Keyword
        keyword_row = QHBoxLayout()
        keyword_lbl = QLabel("키워드:")
        keyword_lbl.setMinimumWidth(100)
        keyword_row.addWidget(keyword_lbl)

        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("검색 키워드 (선택사항)")
        self.keyword_input.setStyleSheet(Style.lineedit())
        keyword_row.addWidget(self.keyword_input, 1)

        filter_layout.addLayout(keyword_row)

        # Skip processed checkbox
        self.skip_processed_checkbox = QCheckBox("이미 처리된 폴더 건너뛰기")
        self.skip_processed_checkbox.setStyleSheet(Style.checkbox())
        self.skip_processed_checkbox.setCursor(QCursor(Qt.PointingHandCursor))
        filter_layout.addWidget(self.skip_processed_checkbox)

        main_layout.addWidget(filter_card)

        # Output card
        output_card = self.create_card()
        output_layout = QVBoxLayout(output_card)
        output_layout.setSpacing(8)

        output_label = QLabel("저장 위치")
        output_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Style.TEXT_PRIMARY};")
        output_layout.addWidget(output_label)

        output_combo_row = QHBoxLayout()
        self.output_combo = NoWheelComboBox()
        self.output_combo.addItems(["각 폴더에 저장", "하나의 폴더에 저장"])
        self.output_combo.setStyleSheet(Style.combobox())
        self.output_combo.currentTextChanged.connect(self.toggle_output_button)
        output_combo_row.addWidget(self.output_combo)

        output_layout.addLayout(output_combo_row)

        output_row = QHBoxLayout()
        self.output_display = QLabel("저장 폴더 선택")
        self.output_display.setMinimumHeight(40)
        self.output_display.setStyleSheet(f"""
            QLabel {{
                background-color: {Style.BG_CARD};
                padding: 8px;
                border-radius: 6px;
                color: {Style.TEXT_SECONDARY};
                font-size: 11px;
            }}
        """)
        output_row.addWidget(self.output_display, 1)

        self.output_button = QPushButton("폴더 선택")
        self.output_button.setFixedSize(100, 32)
        self.output_button.setStyleSheet(Style.small_button())
        self.output_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.output_button.clicked.connect(self.select_output_folder)
        self.output_button.setEnabled(False)
        output_row.addWidget(self.output_button)

        output_layout.addLayout(output_row)

        main_layout.addWidget(output_card)

        # Logo card
        logo_card = self.create_card()
        logo_layout = QVBoxLayout(logo_card)
        logo_layout.setSpacing(8)

        logo_header = QLabel("로고 추가")
        logo_header.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Style.TEXT_PRIMARY};")
        logo_layout.addWidget(logo_header)

        logo_row = QHBoxLayout()
        logo_name = os.path.basename(self.user_logo_path) if self.user_logo_path else "선택안함"
        self.logo_display = QLabel(logo_name)
        self.logo_display.setMinimumHeight(40)
        self.logo_display.setStyleSheet(f"""
            QLabel {{
                background-color: {Style.BG_CARD};
                padding: 8px;
                border-radius: 6px;
                color: {Style.TEXT_SECONDARY};
                font-size: 11px;
            }}
        """)
        logo_row.addWidget(self.logo_display, 1)

        logo_btn = QPushButton("로고 선택")
        logo_btn.setFixedSize(100, 32)
        logo_btn.setStyleSheet(Style.small_button())
        logo_btn.setCursor(QCursor(Qt.PointingHandCursor))
        logo_btn.clicked.connect(self.select_user_logo)
        logo_row.addWidget(logo_btn)

        logo_layout.addLayout(logo_row)

        main_layout.addWidget(logo_card)

        # Progress card
        progress_card = self.create_card()
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setSpacing(8)

        progress_header = QLabel("진행 상황")
        progress_header.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Style.TEXT_PRIMARY};")
        progress_layout.addWidget(progress_header)

        # Spinner + status
        spinner_layout = QHBoxLayout()
        self.spinner_label = QLabel()
        spinner_path = resource_path("spinner.gif")
        if os.path.exists(spinner_path):
            self.spinner_movie = QMovie(spinner_path)
            self.spinner_movie.setScaledSize(QSize(24, 24))
            self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_label.setVisible(False)
        spinner_layout.addWidget(self.spinner_label)

        self.status_label = QLabel("대기 중")
        self.status_label.setStyleSheet(f"font-size: 13px; color: {Style.TEXT_PRIMARY};")
        spinner_layout.addWidget(self.status_label, 1)

        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Style.ACCENT};")
        spinner_layout.addWidget(self.percent_label)

        progress_layout.addLayout(spinner_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet(Style.progress_bar())
        progress_layout.addWidget(self.progress_bar)

        main_layout.addWidget(progress_card)

        main_layout.addStretch()

        # Button area
        button_layout = QHBoxLayout()

        self.html_button = QPushButton("▶  변환 시작")
        self.html_button.setFixedHeight(40)
        self.html_button.setStyleSheet(Style.success_button())
        self.html_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.html_button.clicked.connect(self.start_html_conversion)
        button_layout.addWidget(self.html_button)

        self.stop_button = QPushButton("■  중지")
        self.stop_button.setFixedHeight(40)
        self.stop_button.setStyleSheet(Style.error_button())
        self.stop_button.setEnabled(False)
        self.stop_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.stop_button.clicked.connect(self.stop_processing)
        button_layout.addWidget(self.stop_button)

        main_layout.addLayout(button_layout)

        # 작업완료 폴더 열기 버튼 (처리 완료 후 표시)
        self.open_folder_button = QPushButton("📁  작업완료 폴더 열기")
        self.open_folder_button.setFixedHeight(40)
        self.open_folder_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Style.SUCCESS};
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #27ae60;
            }}
        """)
        self.open_folder_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.open_folder_button.setVisible(False)  # 초기에는 숨김
        self.completed_folder_path = None  # 완료된 폴더 경로 저장
        main_layout.addWidget(self.open_folder_button)

        # Footer (로고 왼쪽, 버전 정보 오른쪽)
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 10, 0, 0)

        # Left: DLAS logo
        logo_path = resource_path("logo.png")
        if os.path.exists(logo_path):
            logo_label = QLabel()
            logo_pixmap = QPixmap(logo_path)
            scaled_logo = logo_pixmap.scaledToHeight(25, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_logo)
            footer_layout.addWidget(logo_label, alignment=Qt.AlignLeft | Qt.AlignBottom)

        footer_layout.addStretch()

        # Right: Version info
        version_label = QLabel("DLAS v2.3.2 © 2025 Dental Lab Automation Solution - All rights reserved.")
        version_label.setStyleSheet("color: #999999; font-size: 10px;")
        footer_layout.addWidget(version_label, alignment=Qt.AlignRight | Qt.AlignBottom)
        main_layout.addLayout(footer_layout)

    def append_debug(self, msg: str) -> None:
        pass  # 로그 출력 비활성화

    def _blink_status_label(self) -> None:
        """상태 라벨 깜빡임 효과"""
        if self.blink_state:
            self.status_label.setStyleSheet(f"font-size: 13px; color: {Style.ACCENT}; font-weight: bold;")
        else:
            self.status_label.setStyleSheet(f"font-size: 13px; color: {Style.TEXT_PRIMARY};")
        self.blink_state = not self.blink_state

    def _start_blinking(self) -> None:
        """깜빡임 시작"""
        self.blink_timer.start(500)  # 500ms마다 깜빡임

    def _stop_blinking(self) -> None:
        """깜빡임 중지"""
        self.blink_timer.stop()
        self.status_label.setStyleSheet(f"font-size: 13px; color: {Style.TEXT_PRIMARY};")

    def on_progress_update_slot(self, percent: int, message: str) -> None:
        """Progress update slot for signal"""
        self.progress_bar.setValue(percent)
        self.percent_label.setText(f"{percent}%")
        self.status_label.setText(message)
        QApplication.processEvents()

    def update_progress(self, val: float, message: str = None) -> None:
        """
        진행률 업데이트
        Args:
            val: 진행률 (0-100)
            message: 상태 메시지 (None이면 기존 메시지 유지)
        """
        percent = int(val)
        if message:
            self.update_progress_signal.emit(percent, message)
        else:
            self.update_progress_signal.emit(percent, self.status_label.text())
        QApplication.processEvents()

    def select_folder(self) -> None:
        if heartbeat_token:
            send_heartbeat()
        last_folder = self.settings.value("last_folder", "")
        path = QFileDialog.getExistingDirectory(self, "작업 폴더 선택", last_folder)
        if path:
            self.folder_path = path
            self.settings.setValue("last_folder", path)
            self.folder_display.setText(path)
            self.folder_display.setStyleSheet(f"""
                QLabel {{
                    background-color: {Style.BG_CARD};
                    padding: 8px;
                    border-radius: 6px;
                    color: {Style.TEXT_PRIMARY};
                    font-size: 11px;
                }}
            """)

    def select_output_folder(self) -> None:
        last_output = self.settings.value("last_output_folder", "")
        path = QFileDialog.getExistingDirectory(self, "출력 폴더 선택", last_output)
        if path:
            self.output_folder = path
            self.settings.setValue("last_output_folder", path)
            self.output_display.setText(path)
            self.output_display.setStyleSheet(f"""
                QLabel {{
                    background-color: {Style.BG_CARD};
                    padding: 8px;
                    border-radius: 6px;
                    color: {Style.TEXT_PRIMARY};
                    font-size: 11px;
                }}
            """)

    def select_user_logo(self) -> None:
        file_filter = "이미지 (*.png *.jpg *.jpeg *.bmp *.gif)"
        path, _ = QFileDialog.getOpenFileName(self, "로고 선택", filter=file_filter)
        if path:
            self.user_logo_path = path
            self.logo_display.setText(os.path.basename(path))
            self.logo_display.setStyleSheet(f"""
                QLabel {{
                    background-color: {Style.BG_CARD};
                    padding: 8px;
                    border-radius: 6px;
                    color: {Style.TEXT_PRIMARY};
                    font-size: 11px;
                }}
            """)
        else:
            self.user_logo_path = None
            self.logo_display.setText("선택안함")
        self.save_config()

    def open_output_folder(self) -> None:
        """작업완료 폴더 열기"""
        if self.completed_folder_path and os.path.exists(self.completed_folder_path):
            try:
                if sys.platform == "win32":
                    os.startfile(self.completed_folder_path)
                elif sys.platform == "darwin":  # macOS
                    subprocess.Popen(["open", self.completed_folder_path])
                else:  # Linux
                    subprocess.Popen(["xdg-open", self.completed_folder_path])
            except Exception as e:
                QMessageBox.warning(self, "오류", f"폴더를 열 수 없습니다: {str(e)}")

    def toggle_output_button(self, text: str) -> None:
        self.output_button.setEnabled(text == "하나의 폴더에 저장")
        if text != "하나의 폴더에 저장":
            self.output_display.setText("저장 폴더 선택")
            self.output_display.setStyleSheet(f"""
                QLabel {{
                    background-color: {Style.BG_CARD};
                    padding: 8px;
                    border-radius: 6px;
                    color: {Style.TEXT_SECONDARY};
                    font-size: 11px;
                }}
            """)
            self.output_folder = None

    def stop_processing(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            self.stop_requested = True
            self.status_label.setText("중지 중...")
            self.stop_button.setEnabled(False)
            # Stop spinner
            if hasattr(self, 'spinner_movie') and self.spinner_movie:
                self.spinner_movie.stop()
                self.spinner_label.setVisible(False)

    def return_to_module_selection(self) -> None:
        """모듈 셀렉션으로 돌아가기"""
        try:
            if getattr(sys, "frozen", False):
                cmd = [sys.executable]
            else:
                main_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "main.py")
                cmd = [sys.executable, main_path]

            # 토큰과 세션 ID가 있으면 전달
            if heartbeat_token:
                cmd.append(f"--token={heartbeat_token}")
            if heartbeat_session_id:
                cmd.append(f"--sid={heartbeat_session_id}")

            subprocess.Popen(cmd)
            self.close()
        except Exception as e:
            QMessageBox.warning(self, "오류", f"모듈 선택으로 돌아가는 중 오류가 발생했습니다: {e}")

    def start_html_conversion(self) -> None:
        if heartbeat_token:
            send_heartbeat()
        if not self.folder_path:
            QMessageBox.warning(self, "경고", "먼저 작업 폴더를 선택해주세요!")
            return

        manual_mode = self.mode_combo.currentText() == "수동"
        save_single = self.output_combo.currentText() == "하나의 폴더에 저장"

        if save_single and not self.output_folder:
            QMessageBox.information(self, "알림", "출력 폴더를 선택해주세요.")
            self.select_output_folder()
            if not self.output_folder:
                return

        time_opt       = self.time_combo.currentText()
        time_limit_hr  = None if time_opt == "제한없음" else int(time_opt.replace("시간 이내", "").strip())
        keyword        = self.keyword_input.text().strip() or None
        skip_processed = self.skip_processed_checkbox.isChecked()

        folders = find_matching_folders(self.folder_path, time_limit_hr, keyword)
        if not folders:
            self.status_label.setText("조건에 맞는 폴더가 없습니다.")
            return

        # Start spinner
        if hasattr(self, 'spinner_movie') and self.spinner_movie:
            self.spinner_label.setVisible(True)
            self.spinner_movie.start()

        # 작업완료 폴더 열기 버튼 숨기기
        self.open_folder_button.setVisible(False)

        self.status_label.setText("HTML 변환 중...")
        self._start_blinking()  # 깜빡임 시작
        self.update_progress(0, f"HTML 변환 중... (0/{0})")
        total = 0
        processed = 0

        fold_to_cands: list[Tuple[str, list[str]]] = []
        for folder in folders:
            cands = expand_candidates_with_zips(folder)
            fold_to_cands.append((folder, cands))
            total += len(cands)

        if manual_mode:
            for orig_folder, candidates in fold_to_cands:
                for work_folder in candidates:
                    QApplication.processEvents()
                    if skip_processed and is_folder_processed(work_folder):
                        self.append_debug(f"[Skip] {work_folder} – already processed")
                        processed += 1; self.update_progress(processed/total*100, f"HTML 변환 중... ({processed}/{total})"); continue

                    mode = detect_mode(work_folder)
                    stl_paths = find_stl_files(work_folder, log_callback=self.append_debug)
                    if not stl_paths:
                        self.append_debug(f"[Skip] {work_folder} – no STL"); processed += 1; self.update_progress(processed/total*100, f"HTML 변환 중... ({processed}/{total})"); continue

                    default_map = parse_3ox_for_groups(work_folder) if mode=="3shape" else parse_exo_for_groups(work_folder)
                    dlg = ManualGroupDialog([os.path.basename(p) for p in stl_paths], default_map, self)
                    if dlg.exec() != QDialog.Accepted:
                        self.append_debug(f"[Cancel] {work_folder} – user skipped")
                        processed += 1; self.update_progress(processed/total*100, f"HTML 변환 중... ({processed}/{total})"); continue
                    group_map = dlg.mapping()

                    if self.output_folder:
                        html_path = os.path.join(self.output_folder, f"{os.path.basename(work_folder)}.html")
                    else:
                        html_path = os.path.join(work_folder, f"{os.path.basename(work_folder)}.html")

                    try:
                        convert_stls_to_html(
                            stl_paths, html_path, work_folder, mode,
                            log_callback=self.append_debug,
                            user_logo_path=self.user_logo_path,
                            group_override=group_map,
                            progress_callback=self.update_progress
                        )
                        self.append_debug(f"[OK] Saved: {os.path.basename(html_path)}")
                        create_folder_marker(work_folder)
                    except Exception as e:
                        self.append_debug(f"[ERROR] {work_folder}: {e}")

                    processed += 1
                    self.update_progress(processed/total*100, f"HTML 변환 중... ({processed}/{total})")

            self._stop_blinking()  # 깜빡임 중지
            self.status_label.setText("HTML 변환 완료!")
            self.update_progress(100)
            # Stop spinner
            if hasattr(self, 'spinner_movie') and self.spinner_movie:
                self.spinner_movie.stop()
                self.spinner_label.setVisible(False)

            # 작업완료 폴더 경로 설정 및 버튼 표시 (수동 모드)
            if self.output_folder:
                self.completed_folder_path = self.output_folder
            else:
                self.completed_folder_path = self.folder_path
            self.open_folder_button.setVisible(True)
            return

        # ----- Auto 모드 -----
        self.stop_requested = False
        self.html_button.setEnabled(False); self.stop_button.setEnabled(True)

        def worker():
            nonlocal processed
            try:
                for orig_folder, candidates in fold_to_cands:
                    for work_folder in candidates:
                        if self.stop_requested:
                            self.append_debug("[Stop] user interrupted")
                            break
                        self.append_debug(f"----------\n[Folder] {work_folder}")

                        if skip_processed and is_folder_processed(work_folder):
                            self.append_debug("  [Skip] already processed")
                            processed += 1; self.update_progress(processed/total*100, f"HTML 변환 중... ({processed}/{total})"); continue

                        mode = detect_mode(work_folder)
                        stl_paths = find_stl_files(work_folder, log_callback=self.append_debug)
                        if not stl_paths:
                            self.append_debug("  [Skip] no STL files")
                            processed += 1; self.update_progress(processed/total*100, f"HTML 변환 중... ({processed}/{total})"); continue

                        if self.output_folder:
                            html_path = os.path.join(self.output_folder, f"{os.path.basename(work_folder)}.html")
                        else:
                            html_path = os.path.join(work_folder, f"{os.path.basename(work_folder)}.html")

                        # multiprocessing.Process로 각 폴더 처리
                        result_queue = multiprocessing.Queue()
                        worker_process = multiprocessing.Process(
                            target=_run_html_worker_process,
                            args=(result_queue, work_folder, stl_paths, html_path,
                                  mode, self.user_logo_path, skip_processed)
                        )
                        worker_process.start()
                        worker_process.join(timeout=60)  # 60초 타임아웃

                        if worker_process.is_alive():
                            # 타임아웃 발생 - 프로세스 강제 종료
                            worker_process.terminate()
                            worker_process.join(timeout=2)
                            if worker_process.is_alive():
                                worker_process.kill()
                            self.append_debug(f"  [TIMEOUT] 60초 초과 - 다음 케이스로 이동")
                        else:
                            # 프로세스 종료됨 - 결과 확인
                            try:
                                result_type, result_data = result_queue.get_nowait()
                                if result_type == "success":
                                    self.append_debug(f"  [OK] Saved: {result_data}")
                                elif result_type == "skipped":
                                    self.append_debug(f"  [Skip] {result_data}")
                                elif result_type == "error":
                                    self.append_debug(f"  [ERROR] {result_data}")
                            except:
                                if worker_process.exitcode != 0:
                                    self.append_debug(f"  [CRASH] Process crashed - 다음 케이스로 이동")

                        processed += 1
                        self.update_progress(processed/total*100, f"HTML 변환 중... ({processed}/{total})")
            finally:
                self._stop_blinking()  # 깜빡임 중지
                if self.stop_requested:
                    self.status_label.setText("HTML 변환 중지됨")
                else:
                    self.status_label.setText("HTML 변환 완료!")
                    self.update_progress(100)

                    # 작업완료 폴더 경로 설정 및 버튼 표시
                    if save_single and self.output_folder:
                        self.completed_folder_path = self.output_folder
                    else:
                        # 각 폴더에 저장했을 때는 첫 번째 폴더 표시
                        self.completed_folder_path = self.folder_path
                    self.open_folder_button.setVisible(True)

                self.html_button.setEnabled(True); self.stop_button.setEnabled(False)
                # Stop spinner
                if hasattr(self, 'spinner_movie') and self.spinner_movie:
                    self.spinner_movie.stop()
                    self.spinner_label.setVisible(False)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

# ==============================================================================
# main
# ==============================================================================
def main() -> None:
    parse_token_and_sid()
    app = QApplication(sys.argv)
    if heartbeat_token and heartbeat_session_id:
        start_heartbeat()
    gui = STLViewerGUI()
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
