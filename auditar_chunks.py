import os
import re
from glob import glob

BASE_DIR = "base_conhecimento_nivus"
AUDIT_OUTPUT = "relatorio_auditoria.txt"


def parse_chunk_file(filepath: str):
    with open(filepath, encoding="utf-8") as f:
        raw = f.read()
    parts = raw.split("=" * 80)
    if len(parts) < 3:
        return "", raw.strip()
    header = parts[1].strip()
    body = parts[2].strip()
    return header, body


def check_markdown_tables(body: str) -> list:
    issues = []
    lines = body.splitlines()
    table_block = []

    def validate_block(block):
        if len(block) < 2:
            issues.append("Tabela com menos de 2 linhas")
            return
        col_counts = [line.count("|") for line in block]
        if len(set(col_counts)) > 1:
            issues.append(f"Colunas desalinhadas: {col_counts}")
        if "---" not in block[1]:
            issues.append("Tabela sem linha separadora '---'")

    for line in lines:
        if line.strip().startswith("|"):
            table_block.append(line.strip())
        else:
            if table_block:
                validate_block(table_block)
                table_block = []
    if table_block:
        validate_block(table_block)
    return issues


def run_audit():
    files = sorted(glob(os.path.join(BASE_DIR, "*", "*.txt")))
    total = len(files)

    header_errors = []
    tiny_chunks = []
    lowercase_starts = []
    abrupt_endings = []
    table_issues = []
    residual_artifacts = []

    multipart_pair = None
    safety_sample = None
    table_sample = None

    for idx, fp in enumerate(files):
        rel_path = os.path.relpath(fp, BASE_DIR).replace("\\", "/")
        header, body = parse_chunk_file(fp)

        # 1. Valida metadados obrigatórios
        required_keys = ["DOCUMENTO:", "CAPÍTULO:", "SEÇÃO:", "PÁGINAS MANUAL:", "DEPENDÊNCIA VISUAL:"]
        if not all(k in header for k in required_keys):
            header_errors.append(rel_path)

        # Remove tag final de dependência visual para testar pontuação real do texto
        body_core = re.sub(r"\n*\[DEPENDÊNCIA VISUAL:.*?\]\s*$", "", body).strip()

        # 2. Chunks muito curtos (< 250 chars)
        if len(body_core) < 250:
            tiny_chunks.append((rel_path, len(body_core), body_core))

        # 3. Início com letra minúscula (ignorando notas de rodapé tipo 'a)')
        if body_core:
            first_char = body_core[0]
            if first_char.islower() and not re.match(r"^[a-z]\)", body_core):
                lowercase_starts.append((rel_path, body_core[:90]))

            # 4. Término sem pontuação de fechamento esperada
            last_char = body_core[-1]
            if last_char not in ".:)]|!?\"”0123456789":
                abrupt_endings.append((rel_path, body_core[-90:]))

        # 5. Integridade de tabelas
        t_err = check_markdown_tables(body_core)
        if t_err:
            table_issues.append((rel_path, t_err))

        # 6. Glifos PUA residuais ou hifenização quebrada
        if re.search(r"[\uf000-\uf8ff\ufffd]", body_core) or re.search(r"[a-zà-ÿ]{2,}-\n[a-zà-ÿ]{2,}", body_core):
            residual_artifacts.append(rel_path)

        # Coleta amostras estratégicas para inspeção qualitativa
        if multipart_pair is None and "(Parte 1/" in header and idx + 1 < total:
            next_h, next_b = parse_chunk_file(files[idx + 1])
            if "(Parte 2/" in next_h:
                multipart_pair = (rel_path, header, body, os.path.relpath(files[idx + 1], BASE_DIR), next_h, next_b)

        if safety_sample is None and "[PERIGO]" in body and "04_seguranca" in rel_path:
            safety_sample = (rel_path, header, body)

        if table_sample is None and "CONTÉM TABELA: Sim" in header and "22_rodas_e_pneus" in rel_path:
            table_sample = (rel_path, header, body)

    # Gera relatório consolidado
    out = []
    out.append("RELATÓRIO DE AUDITORIA DE QUALIDADE DOS CHUNKS (CRITÉRIO 3)\n" + "=" * 80)
    out.append(f"Total de arquivos auditados: {total}")
    out.append(f"1. Erros de cabeçalho/metadados: {len(header_errors)}")
    out.append(f"2. Chunks curtos (< 250 caracteres): {len(tiny_chunks)}")
    out.append(f"3. Inícios em minúscula (possível quebra de frase): {len(lowercase_starts)}")
    out.append(f"4. Términos sem pontuação terminal: {len(abrupt_endings)}")
    out.append(f"5. Tabelas Markdown com desalinhamento: {len(table_issues)}")
    out.append(f"6. Arquivos com glifos PUA ou hífen quebrado residual: {len(residual_artifacts)}\n")

    out.append("--- DETALHAMENTO DOS CASOS SINALIZADOS ---")
    out.append("\n[Chunks Curtos < 250 chars]")
    for p, sz, txt in tiny_chunks:
        out.append(f"- {p} ({sz} chars): {repr(txt)}")

    out.append("\n[Inícios em Minúscula]")
    for p, snippet in lowercase_starts[:15]:
        out.append(f"- {p}: {repr(snippet)}")

    out.append("\n[Términos sem Pontuação Terminal]")
    for p, snippet in abrupt_endings[:15]:
        out.append(f"- {p}: {repr(snippet)}")

    out.append("\n[Problemas em Tabelas]")
    for p, errs in table_issues:
        out.append(f"- {p}: {errs}")

    out.append("\n" + "=" * 80 + "\nAMOSTRAS ESTRATÉGICAS PARA VALIDAÇÃO SEMÂNTICA\n" + "=" * 80)

    if multipart_pair:
        p1, h1, b1, p2, h2, b2 = multipart_pair
        out.append(f"\n>>> AMOSTRA 1A (TRANSIÇÃO MULTI-PARTE - PARTE 1): {p1}\n{h1}\n---\n{b1[-700:]}")
        out.append(f"\n>>> AMOSTRA 1B (TRANSIÇÃO MULTI-PARTE - PARTE 2): {p2}\n{h2}\n---\n{b2[:700]}")

    if safety_sample:
        p, h, b = safety_sample
        out.append(f"\n>>> AMOSTRA 2 (ALERTA CRÍTICO DE SEGURANÇA): {p}\n{h}\n---\n{b}")

    if table_sample:
        p, h, b = table_sample
        out.append(f"\n>>> AMOSTRA 3 (TABELA TÉCNICA): {p}\n{h}\n---\n{b}")

    report_text = "\n".join(out)
    with open(AUDIT_OUTPUT, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"Auditoria concluída! Arquivo '{AUDIT_OUTPUT}' gerado com sucesso.")
    print("\n".join(out[:10]))


if __name__ == "__main__":
    run_audit()