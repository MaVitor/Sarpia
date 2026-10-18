import fitz

from api.schemas import PaginaTexto

LIMIAR_CHARS_POR_PAGINA = 100
AVISO_ESCANEADO = (
    "O PDF tem pouco texto selecionável; isso pode indicar conteúdo que "
    "precisa de OCR, mas não confirma que o documento seja escaneado."
)


class PDFExtracaoErro(Exception):
    """Erro seguro de leitura ou validação de um PDF."""


def extrair_texto(
    pdf_bytes: bytes, max_paginas: int | None = None
) -> tuple[list[PaginaTexto], str | None]:
    """Extrai texto por página sem carregar páginas acima do limite."""
    if not pdf_bytes:
        raise PDFExtracaoErro("O arquivo PDF está vazio.")
    paginas: list[PaginaTexto] = []
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            if doc.is_encrypted or doc.needs_pass:
                raise PDFExtracaoErro("O PDF protegido por senha não é suportado.")
            if max_paginas is not None and doc.page_count > max_paginas:
                raise PDFExtracaoErro(
                    f"O PDF excede o limite de {max_paginas} páginas."
                )
            for i in range(doc.page_count):
                texto = doc.load_page(i).get_text("text").strip()
                paginas.append(PaginaTexto(numero=i + 1, texto=texto))
    except PDFExtracaoErro:
        raise
    except (fitz.FileDataError, ValueError, RuntimeError) as exc:
        raise PDFExtracaoErro("Não foi possível abrir o PDF enviado.") from exc
    if not paginas:
        return [], "O PDF não contém páginas."
    media = sum(len(p.texto) for p in paginas) / len(paginas)
    aviso = AVISO_ESCANEADO if media < LIMIAR_CHARS_POR_PAGINA else None
    return paginas, aviso
