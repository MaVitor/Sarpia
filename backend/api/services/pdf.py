import fitz  # PyMuPDF

from api.schemas import PaginaTexto

LIMIAR_CHARS_POR_PAGINA = 100
AVISO_ESCANEADO = (
    "Este PDF parece ser escaneado (pouco texto selecionável). "
    "O suporte a OCR para PDFs de imagem está no roadmap."
)


def extrair_texto(pdf_bytes: bytes) -> tuple[list[PaginaTexto], str | None]:
    """Extrai texto página a página e detecta PDF provavelmente escaneado."""
    paginas: list[PaginaTexto] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for i, pagina in enumerate(doc):
            texto = pagina.get_text("text").strip()
            paginas.append(PaginaTexto(numero=i + 1, texto=texto))
    if not paginas:
        return [], AVISO_ESCANEADO
    media = sum(len(p.texto) for p in paginas) / len(paginas)
    aviso = AVISO_ESCANEADO if media < LIMIAR_CHARS_POR_PAGINA else None
    return paginas, aviso
