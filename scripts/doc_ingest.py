import json
import logging
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("doc_ingest")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
SOURCE_DIR = Path(os.getenv("DOC_SOURCE_DIR", BASE_DIR / "docs aqui"))
EXPORT_DIR = Path(os.getenv("DOCLING_EXPORT_DIR", BASE_DIR / "data" / "doc_exports"))

try:
    from agent_local.sync_engine import (
        DOC_KNOWLEDGE_DIR,
        SUPPORTED_DOC_EXTENSIONS,
        run_sync,
        DOCLING_AVAILABLE,
    )
except ImportError as sync_err:
    raise SystemExit(f"Não foi possível importar sync_engine: {sync_err}") from sync_err

DOCLING_RUNTIME_AVAILABLE = False
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat

    DOCLING_RUNTIME_AVAILABLE = True
except ImportError as docling_err:
    DocumentConverter = None  # type: ignore
    InputFormat = None  # type: ignore
    if DOCLING_AVAILABLE:
        raise
    logger.warning(
        "Docling não está disponível neste ambiente. Ingestão de documentos será ignorada. "
        "Instale as dependências para habilitar a extração automatizada."
    )


def ensure_directories():
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    DOC_KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def copy_documents():
    copied = 0
    for file_path in SOURCE_DIR.glob("*"):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_DOC_EXTENSIONS:
            target_path = DOC_KNOWLEDGE_DIR / file_path.name
            shutil.copy2(file_path, target_path)
            copied += 1
    logger.info("Arquivos copiados do repositório origem: %s", copied)
    return copied


def export_docling_json():
    if not DOCLING_RUNTIME_AVAILABLE:
        logger.info("Docling ausente - pulando exportação estruturada de documentos.")
        return 0

    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.DOCX, InputFormat.IMAGE]
    )
    exported = 0
    for doc_path in DOC_KNOWLEDGE_DIR.glob("*"):
        if not doc_path.is_file() or doc_path.suffix.lower() not in SUPPORTED_DOC_EXTENSIONS:
            continue
        try:
            conv_result = converter.convert(doc_path)
            data = conv_result.document.export_to_dict()
            export_name = EXPORT_DIR / f"{doc_path.stem}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            with open(export_name, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
            exported += 1
            logger.info("Exportado JSON Docling: %s", export_name.name)
        except Exception as conv_err:
            logger.error("Falha ao converter %s: %s", doc_path.name, conv_err)
    logger.info("Exportações Docling concluídas: %s arquivo(s)", exported)
    return exported


def ingest_documents():
    ensure_directories()
    copied = copy_documents()
    exported = export_docling_json()

    if copied or exported:
        logger.info("Iniciando sincronização de conhecimento com base nos arquivos...")

    synced = run_sync() or 0

    summary = {
        "documents_copied": copied,
        "documents_converted": exported,
        "knowledge_synced": synced,
        "docling_enabled": DOCLING_RUNTIME_AVAILABLE,
    }
    logger.info(
        "Resumo da ingestão: %s copiados | %s convertidos | %s itens sincronizados",
        copied,
        exported,
        synced,
    )
    return summary


def main():
    ingest_documents()


if __name__ == "__main__":
    main()
