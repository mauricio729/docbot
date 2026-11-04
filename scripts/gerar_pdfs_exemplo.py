"""Gera os PDFs de exemplo da pasta docs/ (políticas de uma loja fictícia).

    python scripts/gerar_pdfs_exemplo.py

Troque esses arquivos pelos documentos reais da empresa e rode a ingestão de novo.
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

DOCS = Path(__file__).resolve().parent.parent / "docs"

CONTENT = {
    "politica-trocas.pdf": [
        ("Política de Trocas e Devoluções · Loja Exemplo", [
            "Esta política vale para todas as compras feitas no site, no aplicativo e pelo WhatsApp da Loja Exemplo.",
            "Arrependimento: pelo Código de Defesa do Consumidor, compras feitas fora da loja física podem ser "
            "devolvidas em até 7 dias corridos após o recebimento, sem precisar informar o motivo. O valor é "
            "devolvido integralmente, incluindo o frete.",
        ]),
        ("Prazo para troca", [
            "Você pode solicitar a troca de um produto em até 30 dias após o recebimento. O produto deve estar sem "
            "sinais de uso, com etiquetas e na embalagem original, acompanhado da nota fiscal.",
            "Para solicitar, envie o número do pedido pelo WhatsApp ou pelo e-mail trocas@lojaexemplo.com.br. "
            "Enviamos um código de postagem dos Correios em até 2 dias úteis.",
        ]),
        None,
        ("Produtos com defeito", [
            "Produtos com defeito de fabricação podem ser trocados em até 90 dias após o recebimento. "
            "Nesses casos a coleta é gratuita e o frete de reenvio é pago pela loja.",
            "Se o produto com defeito não estiver mais disponível em estoque, você pode escolher entre um vale-compra "
            "com o valor pago ou o reembolso.",
        ]),
        ("Reembolso", [
            "O reembolso é feito na mesma forma de pagamento da compra. No cartão de crédito, o estorno aparece "
            "em até duas faturas. No Pix, o valor é devolvido em até 5 dias úteis após recebermos o produto.",
            "Produtos personalizados e itens de higiene pessoal não podem ser trocados, exceto em caso de defeito.",
        ]),
    ],
    "entrega-e-frete.pdf": [
        ("Entrega e Frete · Loja Exemplo", [
            "Enviamos para todo o Brasil pelos Correios e por transportadoras parceiras. O prazo começa a contar "
            "depois da confirmação do pagamento.",
        ]),
        ("Prazos de entrega", [
            "Uberlândia e região: entrega em até 1 dia útil por motoboy próprio para pedidos pagos até as 14h.",
            "Capitais do Sudeste: de 2 a 4 dias úteis. Demais regiões: de 4 a 9 dias úteis.",
            "Você recebe o código de rastreio por e-mail e pelo WhatsApp assim que o pedido é despachado.",
        ]),
        ("Valor do frete", [
            "O frete é grátis para compras acima de R$ 199,00 em todo o Brasil. Para compras abaixo desse valor, "
            "o frete é calculado no carrinho a partir do CEP.",
            "Retirada na loja: gratuita. O pedido fica disponível na Avenida Afonso Pena, 1000, Centro, Uberlândia, "
            "de segunda a sábado, a partir de 2 horas após a confirmação do pagamento.",
        ]),
        ("Entregas que não deram certo", [
            "Se ninguém estiver no endereço, a transportadora faz até 3 tentativas. Depois disso o pedido volta "
            "para a loja e entramos em contato para combinar um novo envio, com novo frete.",
        ]),
    ],
    "pagamentos-e-garantia.pdf": [
        ("Pagamentos · Loja Exemplo", [
            "Aceitamos Pix, cartão de crédito das bandeiras Visa, Mastercard, Elo e American Express, e boleto bancário.",
            "No Pix você ganha 5% de desconto. O código Pix vale por 30 minutos.",
            "No cartão de crédito, parcelamos em até 6 vezes sem juros, com parcela mínima de R$ 50,00. "
            "De 7 a 10 vezes, há juros de 1,99% ao mês.",
            "O boleto vence em 2 dias úteis e o pedido só é separado após a compensação, que leva até 3 dias úteis.",
        ]),
        ("Garantia", [
            "Todos os produtos têm garantia legal de 90 dias. Eletrônicos têm também garantia do fabricante de "
            "12 meses, contada a partir da data da nota fiscal.",
            "Para acionar a garantia do fabricante, procure a assistência técnica autorizada da marca. "
            "Nossa equipe ajuda a encontrar a mais próxima.",
        ]),
        ("Atendimento", [
            "Nosso atendimento humano funciona de segunda a sexta, das 8h às 18h, e aos sábados das 8h às 12h. "
            "O assistente virtual responde 24 horas por dia.",
        ]),
    ],
}


def build(filename: str, sections: list) -> None:
    styles = getSampleStyleSheet()
    story = []
    for i, section in enumerate(sections):
        if section is None:
            story.append(PageBreak())
            continue
        title, paragraphs = section
        story.append(Paragraph(title, styles["Title"] if i == 0 else styles["Heading2"]))
        for p in paragraphs:
            story.append(Paragraph(p, styles["BodyText"]))
            story.append(Spacer(1, 6))
    SimpleDocTemplate(str(DOCS / filename), pagesize=A4, title=filename).build(story)


if __name__ == "__main__":
    DOCS.mkdir(exist_ok=True)
    for name, sections in CONTENT.items():
        build(name, sections)
        print(f"docs/{name}")
