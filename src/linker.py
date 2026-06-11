"""Lógica de vinculação de itens a produto_canonico."""



def link_item(item: dict) -> dict:
    """
    Tenta vincular automaticamente um item a um produto_canonico.

    Retorna:
        {
            "status": "linked" | "suggested" | "unmatched",
            "id_produto_canonico": int or None,
            "suggestions": list of {"id": int, "nome": str, "score": float}
        }
    """
    from .db import find_produto_by_ean, find_alias, find_similar_aliases

    ean = item.get("ean") or ""
    cnpj = item.get("cnpj_emitente") or ""
    codigo = item.get("codigo_produto_nota") or ""
    descricao = item.get("descricao_nota") or ""

    # 1. Tenta por EAN
    if ean and ean.upper() not in ("SEM GTIN", ""):
        produto = find_produto_by_ean(ean)
        if produto:
            return {
                "status": "linked",
                "id_produto_canonico": produto["id"],
                "suggestions": [],
            }

    # 2. Tenta por alias (cnpj + codigo_produto)
    if cnpj and codigo:
        alias = find_alias(cnpj, codigo)
        if alias:
            return {
                "status": "linked",
                "id_produto_canonico": alias["id_produto_canonico"],
                "suggestions": [],
            }

    # 3. Busca aliases similares
    similares = find_similar_aliases(descricao, limit=5)
    suggestions = []
    for alias_row, score in similares:
        if score > 0.6:
            suggestions.append({
                "id": alias_row["id_produto_canonico"],
                "nome": alias_row.get("pc_nome") or alias_row.get("descricao_nota", ""),
                "score": round(score, 4),
            })

    if suggestions:
        return {
            "status": "suggested",
            "id_produto_canonico": None,
            "suggestions": suggestions,
        }

    return {
        "status": "unmatched",
        "id_produto_canonico": None,
        "suggestions": [],
    }
