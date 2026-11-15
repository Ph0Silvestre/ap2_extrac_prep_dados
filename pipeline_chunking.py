import json
import os
import re
import shutil
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import fitz  # PyMuPDF


PDF_PATH = "Manual de instruções - NIVUS.pdf"
OUTPUT_DIR = "base_conhecimento_nivus"
METRICS_PATH = "relatorio_metricas.json"

MAX_CHUNK_CHARS = 2400
MIN_CHUNK_CHARS = 220
OVERLAP_CHARS = 220

CHAPTER_MAP = [
    (0, 3, "00_garantia_e_plano_digital", "Garantia e Plano Digital de Serviços"),
    (4, 5, "00_indice_geral", "Índice Geral"),
    (6, 8, "01_sobre_o_manual", "Sobre este Manual de instruções"),
    (9, 14, "02_vista_geral_do_veiculo", "Vista geral do veículo"),
    (15, 31, "03_informacoes_ao_condutor", "Informações ao condutor"),
    (32, 63, "04_seguranca", "Segurança"),
    (64, 77, "05_abrir_e_fechar", "Abrir e fechar"),
    (78, 78, "06_volante", "Volante"),
    (79, 84, "07_bancos_e_apoios_para_cabeca", "Bancos e apoios para cabeça"),
    (85, 89, "08_iluminacao", "Iluminação"),
    (90, 95, "09_visibilidade", "Visibilidade"),
    (96, 100, "10_aquecimento_e_ar_condicionado", "Aquecimento e ar-condicionado"),
    (101, 118, "11_conduzir", "Conduzir"),
    (119, 130, "12_sistemas_de_assistencia_ao_condutor", "Sistemas de assistência ao condutor"),
    (131, 140, "13_estacionar_e_manobrar", "Estacionar e manobrar"),
    (141, 144, "14_equipamentos_praticos", "Equipamentos práticos"),
    (145, 148, "15_radios", "Rádios"),
    (149, 178, "16_composition_touch", "Composition Touch (R 340G)"),
    (179, 188, "17_vw_play", "VW Play"),
    (189, 198, "18_transportar", "Transportar"),
    (199, 204, "19_combustivel", "Combustível"),
    (205, 220, "20_autoajuda", "Autoajuda"),
    (221, 239, "21_verificacao_e_reabastecimento", "Verificação e reabastecimento"),
    (240, 257, "22_rodas_e_pneus", "Rodas e pneus"),
    (258, 275, "23_manutencao", "Manutenção"),
    (276, 281, "24_informacoes_ao_consumidor", "Informações ao consumidor"),
    (281, 286, "25_dados_tecnicos", "Dados técnicos"),
    (287, 305, "26_abreviaturas_e_indice_remissivo", "Abreviaturas e Índice remissivo"),
]

CHAPTER_TITLE_LOOKUP = {
    "índice": ("00_indice_geral", "Índice Geral"),
    "sobre este manual de instruções": ("01_sobre_o_manual", "Sobre este Manual de instruções"),
    "vista geral do veículo": ("02_vista_geral_do_veiculo", "Vista geral do veículo"),
    "informações ao condutor": ("03_informacoes_ao_condutor", "Informações ao condutor"),
    "segurança": ("04_seguranca", "Segurança"),
    "abrir e fechar": ("05_abrir_e_fechar", "Abrir e fechar"),
    "volante": ("06_volante", "Volante"),
    "bancos e apoios para cabeça": ("07_bancos_e_apoios_para_cabeca", "Bancos e apoios para cabeça"),
    "iluminação": ("08_iluminacao", "Iluminação"),
    "visibilidade": ("09_visibilidade", "Visibilidade"),
    "aquecimento e ar-condicionado": ("10_aquecimento_e_ar_condicionado", "Aquecimento e ar-condicionado"),
    "conduzir": ("11_conduzir", "Conduzir"),
    "sistemas de assistência ao condutor": ("12_sistemas_de_assistencia_ao_condutor", "Sistemas de assistência ao condutor"),
    "estacionar e manobrar": ("13_estacionar_e_manobrar", "Estacionar e manobrar"),
    "equipamentos práticos": ("14_equipamentos_praticos", "Equipamentos práticos"),
    "rádios": ("15_radios", "Rádios"),
    "composition touch (r 340g)": ("16_composition_touch", "Composition Touch (R 340G)"),
    "vw play": ("17_vw_play", "VW Play"),
    "transportar": ("18_transportar", "Transportar"),
    "combustível": ("19_combustivel", "Combustível"),
    "autoajuda": ("20_autoajuda", "Autoajuda"),
    "verificação e reabastecimento": ("21_verificacao_e_reabastecimento", "Verificação e reabastecimento"),
    "rodas e pneus": ("22_rodas_e_pneus", "Rodas e pneus"),
    "manutenção": ("23_manutencao", "Manutenção"),
    "informações ao consumidor": ("24_informacoes_ao_consumidor", "Informações ao consumidor"),
    "dados técnicos": ("25_dados_tecnicos", "Dados técnicos"),
    "abreviaturas utilizadas": ("26_abreviaturas_e_indice_remissivo", "Abreviaturas e Índice remissivo"),
}

OFFICIAL_TOC_SECTIONS = {
    "vista frontal", "vista traseira", "porta do condutor", "lado do condutor",
    "console central", "lado do passageiro dianteiro", "símbolos no revestimento do teto",
    "luzes de advertência e de controle", "instrumento combinado",
    "comando do instrumento combinado", "comando e indicações no rádio",
    "orientações gerais", "ajustar a posição do banco", "cintos de segurança",
    "sistema de airbag", "transporte de crianças no veículo", "em caso de emergência",
    "chave do veículo", "sistema de travamento e de partida sem chave",
    "portas e botão do travamento central", "sistema de alarme antifurto",
    "monitoramento do interior do veículo", "tampa traseira", "vidros",
    "ajustar a posição do volante", "banco dianteiro", "bancos traseiros",
    "apoios para cabeça", "funções do banco", "indicadores de direção",
    "luzes de condução", "iluminação interna", "limpadores e lavadores dos vidros",
    "espelhos retrovisores", "proteção solar", "aquecer, ventilar, refrigerar",
    "orientações para condução", "ligar e desligar o motor", "transmissão automática",
    "sistema de assistência nas subidas", "direção assistida",
    "sistema regulador de velocidade (gra)", "limitador de velocidade",
    "controle automático de distância (acc)",
    "assistente de frenagem de emergência (front assist)",
    "estacionar", "freio de estacionamento",
    "orientações de segurança para sistemas de estacionamento",
    "auxílio de estacionamento (park pilot)", "câmera de marcha a ré (rear view)",
    "sistemas de assistência à frenagem", "porta-objetos", "porta-copos", "tomada",
    "antes do primeiro uso", "outros documentos aplicáveis", "vista geral de conforto",
    "recomendações de segurança", "indicações de utilização", "gestão de energia",
    "codificação antifurto", "display", "vista geral do aparelho",
    "informações básicas de comando", "conectividade", "operação do rádio",
    "operação de mídia", "conexões com e sem fios", "telefone", "configurações",
    "bem-vindo ao vw play", "telas de acesso rápido", "rádio", "mídia",
    "conecte-se", "app store", "apple carplay", "android auto",
    "acomodar volumes de bagagem", "compartimento de bagagem", "bagageiro do teto",
    "condução com reboque", "orientações de segurança para o manuseio de combustível",
    "tipos de combustível e abastecimento",
    "unidade de controle do motor e sistema de controle de emissões dos gases de escape",
    "qualidade dos combustíveis", "ferramentas de bordo",
    "palhetas dos limpadores dos vidros", "iluminação externa", "fusíveis",
    "auxílio à partida", "puxar e rebocar", "no compartimento do motor",
    "fluidos e recursos", "água dos lavadores dos vidros", "óleo do motor",
    "líquido de arrefecimento do motor", "fluido de freio", "bateria do veículo",
    "sistema de controle dos pneus", "informações importantes sobre rodas e pneus",
    "troca de roda", "serviço", "conservação do veículo",
    "acessórios, reposição de peças, reparos e modificações",
    "garantia volkswagen", "etiquetas adesivas e plaquetas",
    "recepção do rádio e antena", "instalar o rádio",
    "volume do rádio ou do sistema de navegação", "fone de ouvido",
    "serviço de atendimento ao cliente", "declaração de conformidade",
    "licença de utilização (anatel)", "orientações sobre os dados técnicos",
    "dados de identificação do veículo", "informações do ar-condicionado",
    "dimensões", "capacidades", "motor 1.0 totalflex 85/94 kw - tsi",
    "abreviaturas utilizadas", "índice remissivo",
}

COMPOUND_PREFIXES = (
    "ar", "para", "porta", "pré", "pós", "anti", "auto", "semi", "sub",
    "super", "micro", "multi", "descansa", "lava", "guarda", "contra",
    "extra", "infra", "intra", "ultra", "vice", "ex", "bem", "mal", "recém",
    "ano", "baixa", "alta", "meio", "corta", "tapa", "limpa"
)


@dataclass
class TextBlock:
    text: str
    font_size: float
    is_bold: bool
    manual_page: int
    pdf_page: int
    is_table: bool = False
    is_heading: bool = False


@dataclass
class SectionUnit:
    chapter_folder: str
    chapter_title: str
    section_title: str
    blocks: List[TextBlock] = field(default_factory=list)


def get_fallback_chapter(manual_page: int) -> Tuple[str, str]:
    for start, end, folder, title in CHAPTER_MAP:
        if start <= manual_page <= end:
            return folder, title
    return "26_abreviaturas_e_indice_remissivo", "Abreviaturas e Índice remissivo"


def get_manual_page_number(pdf_idx: int) -> int:
    if pdf_idx <= 1:
        return 0
    return pdf_idx - 1


def clean_vw_glyphs_and_text(text: str, is_table: bool = False) -> str:
    text = re.sub(r"\b21B\.5B1\.NIV\.66\b", "", text)
    text = re.sub(r"^\d{1,3}\s+Manual de instruções\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[\uf000-\uf8ff\ufffd▷◁►◄■□▪▫]", " ", text)
    text = re.sub(r"\s*→\s*", " -> ", text)

    if is_table:
        lines = [re.sub(r"[ \t]{2,}", " ", ln).strip() for ln in text.splitlines()]
        return "\n".join(ln for ln in lines if ln)

    # Evita que barras literais em texto corrido (ex: "A | B - Função") sejam lidas como tabela
    text = text.replace("|", "/")

    text = re.sub(
        r"(?:^|\n)\s*(?:A\s+)?(PERIGO|ATENÇÃO|CUIDADO)\s*(?=\n|$)",
        r"\n[\1]\n",
        text,
    )
    text = re.sub(r"(?:^|\n)\s*NOTA\s*(?=\n|$)", r"\n[NOTA]\n", text)
    text = re.sub(r"^\s*[•●✓–]\s*", "- ", text, flags=re.MULTILINE)

    def _dehyphenate(match: re.Match) -> str:
        prefix, suffix = match.group(1), match.group(2)
        if prefix.lower() in COMPOUND_PREFIXES:
            return f"{prefix}-{suffix}"
        return f"{prefix}{suffix}"

    text = re.sub(
        r"\b([A-Za-zÀ-ÿ]{2,})-\s*\n\s*([a-zà-ÿ]{2,})\b",
        _dehyphenate,
        text,
    )

    text = re.sub(r"(?<!\n)\n(?!\n|- |\[)", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_tables_markdown(page: fitz.Page) -> Tuple[List[str], List[fitz.Rect]]:
    md_tables = []
    table_rects = []
    try:
        tables = page.find_tables()
    except Exception:
        return md_tables, table_rects

    for tab in tables:
        cleaned_rows = []
        for row in tab.rows:
            cells = []
            for cell_box in row.cells:
                if cell_box is None:
                    cells.append("")
                    continue
                rect = fitz.Rect(cell_box)
                raw_cell = page.get_text("text", clip=rect)
                raw_cell = re.sub(r"([A-Za-zÀ-ÿ]{2,})-\s*\n\s*([a-zà-ÿ]{2,})", r"\1\2", raw_cell)
                cell_txt = re.sub(r"\s+", " ", raw_cell).strip().replace("|", "/")
                cells.append(cell_txt)
            if any(cells):
                cleaned_rows.append(cells)

        if len(cleaned_rows) < 2:
            continue

        col_count = max(len(r) for r in cleaned_rows)
        norm_rows = [r + [""] * (col_count - len(r)) for r in cleaned_rows]

        header = "| " + " | ".join(norm_rows[0]) + " |"
        sep = "| " + " | ".join(["---"] * col_count) + " |"
        body = ["| " + " | ".join(r) + " |" for r in norm_rows[1:]]
        md_tables.append("\n".join([header, sep] + body))
        table_rects.append(fitz.Rect(tab.bbox))

    return md_tables, table_rects


def rect_overlaps_any(rect: fitz.Rect, targets: List[fitz.Rect], threshold: float = 0.5) -> bool:
    for t in targets:
        inter = rect & t
        if not inter.is_empty:
            if (inter.get_area() / max(rect.get_area(), 1.0)) >= threshold:
                return True
    return False


def parse_pdf_blocks(pdf_path: str) -> List[TextBlock]:
    doc = fitz.open(pdf_path)
    all_blocks: List[TextBlock] = []

    for pdf_idx, page in enumerate(doc):
        pdf_page_num = pdf_idx + 1
        if pdf_idx == 0 or pdf_idx == len(doc) - 1:
            continue

        manual_page = get_manual_page_number(pdf_idx)
        w, h = page.rect.width, page.rect.height
        mid_x = w / 2.0
        top_margin, bottom_margin = 48, h - 48

        md_tables, table_rects = extract_tables_markdown(page)
        page_dict = page.get_text("dict")
        left_col, right_col = [], []

        for b in page_dict.get("blocks", []):
            if b.get("type") != 0:
                continue
            bbox = fitz.Rect(b["bbox"])
            if bbox.y1 < top_margin or bbox.y0 > bottom_margin:
                continue
            if rect_overlaps_any(bbox, table_rects):
                continue

            lines_text = []
            max_font = 0.0
            bold_chars = 0
            total_chars = 0

            for line in b.get("lines", []):
                spans_str = []
                for span in line.get("spans", []):
                    s_txt = span.get("text", "")
                    if not s_txt.strip():
                        spans_str.append(s_txt)
                        continue
                    f_size = span.get("size", 9.0)
                    f_flags = span.get("flags", 0)
                    f_name = span.get("font", "").lower()
                    is_b = bool(f_flags & 16) or ("bold" in f_name) or ("black" in f_name)

                    max_font = max(max_font, f_size)
                    total_chars += len(s_txt.strip())
                    if is_b:
                        bold_chars += len(s_txt.strip())
                    spans_str.append(s_txt)
                lines_text.append("".join(spans_str))

            raw_block = "\n".join(lines_text).strip()
            if not raw_block:
                continue

            cleaned = clean_vw_glyphs_and_text(raw_block, is_table=False)
            if not cleaned or len(cleaned) < 2:
                continue

            is_bold = (bold_chars / max(total_chars, 1)) > 0.65
            tb = TextBlock(
                text=cleaned,
                font_size=round(max_font, 1),
                is_bold=is_bold,
                manual_page=manual_page,
                pdf_page=pdf_page_num,
                is_table=False,
            )

            if bbox.x0 < mid_x - 15:
                left_col.append((bbox.y0, tb))
            else:
                right_col.append((bbox.y0, tb))

        left_col.sort(key=lambda item: item[0])
        right_col.sort(key=lambda item: item[0])

        for _, tb in left_col:
            all_blocks.append(tb)
        for _, tb in right_col:
            all_blocks.append(tb)

        for md_tab in md_tables:
            cleaned_tab = clean_vw_glyphs_and_text(md_tab, is_table=True)
            all_blocks.append(
                TextBlock(
                    text=cleaned_tab,
                    font_size=8.5,
                    is_bold=False,
                    manual_page=manual_page,
                    pdf_page=pdf_page_num,
                    is_table=True,
                )
            )

    doc.close()
    return all_blocks


def is_valid_section_heading(b: TextBlock, chap_title: str) -> bool:
    if b.is_table or not b.is_bold or len(b.text) > 95:
        return False
    norm = re.sub(r"\s+", " ", b.text.lower()).strip()
    if norm == chap_title.lower().strip():
        return False
    if re.match(r"^(observe|legenda para|fig\.|atenção|perigo|cuidado|nota|\[)", norm):
        return False
    if norm in OFFICIAL_TOC_SECTIONS and b.font_size >= 9.0:
        return True
    return b.font_size >= 12.0


def merge_broken_prose_blocks(blocks: List[TextBlock]) -> List[TextBlock]:
    merged: List[TextBlock] = []
    for b in blocks:
        if not merged:
            merged.append(b)
            continue

        prev = merged[-1]
        can_merge = (
            not prev.is_table
            and not b.is_table
            and not prev.is_heading
            and not b.is_heading
            and not prev.text.startswith("[")
            and not b.text.startswith("[")
            and not b.text.startswith("- ")
            and not re.match(r"^(Fig\.|Legenda para|Observe\b)", b.text)
            and abs(b.manual_page - prev.manual_page) <= 1
        )

        if can_merge:
            m_hyph = re.search(r"([A-Za-zÀ-ÿ]{2,})-$", prev.text)
            if m_hyph and b.text and b.text[0].islower():
                prefix = m_hyph.group(1)
                joiner = "-" if prefix.lower() in COMPOUND_PREFIXES else ""
                prev.text = prev.text[:-1] + joiner + b.text
                continue

            if prev.text[-1] not in ".!?:;)]\"”":
                prev.text = prev.text.rstrip() + " " + b.text.lstrip()
                continue

        merged.append(b)
    return merged


def group_into_sections(blocks: List[TextBlock]) -> List[SectionUnit]:
    curr_folder, curr_chap = "00_garantia_e_plano_digital", "Garantia e Plano Digital de Serviços"
    tagged_blocks: List[Tuple[str, str, TextBlock]] = []

    for b in blocks:
        norm = re.sub(r"\s+", " ", b.text.lower()).strip()

        # 1. Troca explícita pelo título oficial do capítulo
        if not b.is_table and len(norm) <= 65 and norm in CHAPTER_TITLE_LOOKUP and (b.font_size >= 13.5 or b.is_bold):
            cand_folder, cand_chap = CHAPTER_TITLE_LOOKUP[norm]
            fb_folder, _ = get_fallback_chapter(b.manual_page)
            if cand_folder == fb_folder or abs(int(cand_folder[:2]) - int(fb_folder[:2])) <= 1:
                curr_folder, curr_chap = cand_folder, cand_chap
                continue

        # 2. Fallback determinístico por faixa de páginas (evita absorver capítulos gráficos)
        fb_folder, fb_chap = get_fallback_chapter(b.manual_page)
        if int(fb_folder[:2]) > int(curr_folder[:2]):
            # Mantém no capítulo anterior apenas se for continuação direta de frase em minúscula
            if not (b.text and b.text[0].islower()):
                curr_folder, curr_chap = fb_folder, fb_chap

        b.is_heading = is_valid_section_heading(b, curr_chap)
        tagged_blocks.append((curr_folder, curr_chap, b))

    raw_sections: List[SectionUnit] = []
    current_section: Optional[SectionUnit] = None

    for folder, chap_title, b in tagged_blocks:
        if current_section is None or current_section.chapter_folder != folder:
            sec_name = b.text if b.is_heading else f"Visão Geral - {chap_title}"
            current_section = SectionUnit(
                chapter_folder=folder,
                chapter_title=chap_title,
                section_title=sec_name,
            )
            raw_sections.append(current_section)
            if not b.is_heading:
                current_section.blocks.append(b)
        elif b.is_heading and len(current_section.blocks) > 0:
            current_section = SectionUnit(
                chapter_folder=folder,
                chapter_title=chap_title,
                section_title=b.text,
            )
            raw_sections.append(current_section)
        else:
            current_section.blocks.append(b)

    clean_sections: List[SectionUnit] = []
    for sec in raw_sections:
        sec.blocks = merge_broken_prose_blocks(sec.blocks)
        if not sec.blocks:
            continue

        sec_len = sum(len(x.text) for x in sec.blocks)
        if (
            sec_len < MIN_CHUNK_CHARS
            and clean_sections
            and clean_sections[-1].chapter_folder == sec.chapter_folder
        ):
            title_block = TextBlock(
                text=sec.section_title,
                font_size=11.0,
                is_bold=True,
                manual_page=sec.blocks[0].manual_page,
                pdf_page=sec.blocks[0].pdf_page,
                is_heading=True,
            )
            clean_sections[-1].blocks.append(title_block)
            clean_sections[-1].blocks.extend(sec.blocks)
        else:
            clean_sections.append(sec)

    return clean_sections


def sanitize_filename(name: str, max_len: int = 45) -> str:
    name = name.lower()
    replacements = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e", "í": "i", "ó": "o",
        "ô": "o", "õ": "o", "ú": "u", "ç": "c",
    }
    for k, v in replacements.items():
        name = name.replace(k, v)
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return name[:max_len].strip("_") or "secao"


def build_chunks_and_export(sections: List[SectionUnit]) -> Dict:
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    global_chunk_id = 1
    stats = {
        "total_chunks": 0,
        "total_pastas": 0,
        "chunks_com_dependencia_visual": 0,
        "chunks_com_tabelas": 0,
        "chunks_com_alertas_seguranca": 0,
        "tamanho_medio_caracteres": 0,
        "tamanho_min_caracteres": 10**9,
        "tamanho_max_caracteres": 0,
        "distribuicao_por_pasta": {},
    }
    total_chars_acc = 0

    for sec in sections:
        if not sec.blocks:
            continue

        folder_path = os.path.join(OUTPUT_DIR, sec.chapter_folder)
        os.makedirs(folder_path, exist_ok=True)

        sub_chunks: List[List[TextBlock]] = []
        curr_blocks: List[TextBlock] = []
        curr_len = 0

        for b in sec.blocks:
            b_len = len(b.text)
            last_block = curr_blocks[-1] if curr_blocks else None
            # Nunca encerra um chunk em subtítulo ou chamada introdutória (":")
            prevent_split = bool(
                last_block and (last_block.text.endswith(":") or last_block.is_heading)
            )

            if curr_blocks and (curr_len + b_len > MAX_CHUNK_CHARS) and not prevent_split:
                sub_chunks.append(curr_blocks)
                if not last_block.is_table and not last_block.is_heading and len(last_block.text) <= OVERLAP_CHARS * 2:
                    curr_blocks = [last_block, b]
                    curr_len = len(last_block.text) + b_len
                else:
                    curr_blocks = [b]
                    curr_len = b_len
            else:
                curr_blocks.append(b)
                curr_len += b_len

        if curr_blocks:
            tail_len = sum(len(x.text) for x in curr_blocks)
            if len(sub_chunks) > 0 and tail_len < MIN_CHUNK_CHARS:
                for x in curr_blocks:
                    if x not in sub_chunks[-1]:
                        sub_chunks[-1].append(x)
            else:
                sub_chunks.append(curr_blocks)

        total_parts = len(sub_chunks)
        for part_idx, chunk_blocks in enumerate(sub_chunks, start=1):
            body_text = "\n\n".join(cb.text for cb in chunk_blocks)
            manual_pages = sorted({cb.manual_page for cb in chunk_blocks})
            pdf_pages = sorted({cb.pdf_page for cb in chunk_blocks})

            figs = sorted(set(re.findall(r"Fig\.\s*\d+[A-Z0-9]*", body_text)))
            alerts = sorted(set(re.findall(r"\[(PERIGO|ATENÇÃO|CUIDADO|NOTA)\]", body_text)))
            has_table = any(cb.is_table for cb in chunk_blocks)
            has_visual_dep = len(figs) > 0

            if has_visual_dep:
                body_text += f"\n\n[DEPENDÊNCIA VISUAL: Este trecho referencia {', '.join(figs)} no manual original.]"

            p_man_str = (
                f"{manual_pages[0]}"
                if len(manual_pages) == 1
                else f"{manual_pages[0]}-{manual_pages[-1]}"
            )
            p_pdf_str = (
                f"{pdf_pages[0]}"
                if len(pdf_pages) == 1
                else f"{pdf_pages[0]}-{pdf_pages[-1]}"
            )

            header = (
                "================================================================================\n"
                "DOCUMENTO: Manual de Instruções - Volkswagen Nivus (Código: 21B.5B1.NIV.66)\n"
                f"CAPÍTULO: {sec.chapter_title}\n"
                f"SEÇÃO: {sec.section_title} (Parte {part_idx}/{total_parts})\n"
                f"PÁGINAS MANUAL: {p_man_str} (PDF: {p_pdf_str})\n"
                f"FIGURAS REFERENCIADAS: {', '.join(figs) if figs else 'Nenhuma'}\n"
                f"ALERTAS PRESENTES: {', '.join(alerts) if alerts else 'Nenhum'}\n"
                f"CONTÉM TABELA: {'Sim' if has_table else 'Não'}\n"
                f"DEPENDÊNCIA VISUAL: {'Sim' if has_visual_dep else 'Não'}\n"
                "================================================================================\n\n"
            )

            full_content = header + body_text
            sec_slug = sanitize_filename(sec.section_title)
            filename = f"chunk_{global_chunk_id:04d}_{sec_slug}.txt"
            filepath = os.path.join(folder_path, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_content)

            c_len = len(body_text)
            total_chars_acc += c_len
            stats["total_chunks"] += 1
            stats["tamanho_min_caracteres"] = min(stats["tamanho_min_caracteres"], c_len)
            stats["tamanho_max_caracteres"] = max(stats["tamanho_max_caracteres"], c_len)
            if has_visual_dep:
                stats["chunks_com_dependencia_visual"] += 1
            if has_table:
                stats["chunks_com_tabelas"] += 1
            if alerts:
                stats["chunks_com_alertas_seguranca"] += 1

            stats["distribuicao_por_pasta"][sec.chapter_folder] = (
                stats["distribuicao_por_pasta"].get(sec.chapter_folder, 0) + 1
            )
            global_chunk_id += 1

    stats["total_pastas"] = len(stats["distribuicao_por_pasta"])
    if stats["total_chunks"] > 0:
        stats["tamanho_medio_caracteres"] = round(
            total_chars_acc / stats["total_chunks"], 1
        )
    else:
        stats["tamanho_min_caracteres"] = 0

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return stats


if __name__ == "__main__":
    blocks = parse_pdf_blocks(PDF_PATH)
    sections = group_into_sections(blocks)
    metrics = build_chunks_and_export(sections)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))