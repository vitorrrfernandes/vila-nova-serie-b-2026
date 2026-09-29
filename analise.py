# %%
import json
from pathlib import Path
import pandas as pd

eventos = []
for a in sorted(Path("data/raw").glob("rodada_*.json")):
    eventos += json.loads(a.read_text(encoding="utf-8"))["events"]

print(len(eventos))
print(len({e["id"] for e in eventos}))
# %%
pd.Series([e["status"]["type"] for e in eventos]).value_counts()
# %%
adiados = [e for e in eventos if e["status"]["type"] == "postponed"]

for e in adiados:
    mesmo_confronto = [
        (o["roundInfo"]["round"], o["status"]["type"])
        for o in eventos
        if o["homeTeam"]["id"] == e["homeTeam"]["id"]
        and o["awayTeam"]["id"] == e["awayTeam"]["id"]
    ]
    print(e["roundInfo"]["round"], e["homeTeam"]["name"], "x", e["awayTeam"]["name"], "->", mesmo_confronto)

# %%
finalizados = [e for e in eventos if e["status"]["type"] == "finished"]
print(len(finalizados))
# %%
jogos = pd.DataFrame([{
    "id_jogo": e["id"],
    "rodada": e["roundInfo"]["round"],
    "data": (pd.to_datetime(e["startTimestamp"], unit="s", utc=True)
               .tz_convert("America/Sao_Paulo").tz_localize(None)),
    "mandante": e["homeTeam"]["name"],
    "visitante": e["awayTeam"]["name"],
    "gols_mand": e["homeScore"].get("normaltime"),
    "gols_mand_1t": e["homeScore"].get("period1"),
    "gols_mand_2t": e["homeScore"].get("period2"),
    "gols_vis": e["awayScore"].get("normaltime"),
    "gols_vis_1t": e["awayScore"].get("period1"),
    "gols_vis_2t": e["awayScore"].get("period2"),
} for e in finalizados])

jogos.head(10)
# %%
print(jogos.isna().sum())

soma_ok = (
    (jogos.gols_mand == jogos.gols_mand_1t + jogos.gols_mand_2t)
    & (jogos.gols_vis == jogos.gols_vis_1t + jogos.gols_vis_2t)
)
print("Jogos em que 1T + 2T não bate com o total:", (~soma_ok).sum())
# %%
casa = jogos.rename(columns={
    "mandante": "time", "visitante": "adversario",
    "gols_mand": "gols_pro", "gols_mand_1t": "gols_pro_1t", "gols_mand_2t": "gols_pro_2t",
    "gols_vis": "gols_contra", "gols_vis_1t": "gols_contra_1t", "gols_vis_2t": "gols_contra_2t",
}).assign(mando="Casa")

fora = jogos.rename(columns={
    "visitante": "time", "mandante": "adversario",
    "gols_vis": "gols_pro", "gols_vis_1t": "gols_pro_1t", "gols_vis_2t": "gols_pro_2t",
    "gols_mand": "gols_contra", "gols_mand_1t": "gols_contra_1t", "gols_mand_2t": "gols_contra_2t",
}).assign(mando="Fora")

longo = pd.concat([casa, fora], ignore_index=True)
print(len(longo))
longo[longo["time"] == "Vila Nova FC"].sort_values("data").head(5)
# %%
import numpy as np

longo["resultado"] = np.select(
    [longo.gols_pro > longo.gols_contra, longo.gols_pro == longo.gols_contra],
    ["V", "E"],
    default="D",
)
longo["pontos"] = longo["resultado"].map({"V": 3, "E": 1, "D": 0})

longo[longo["time"] == "Vila Nova FC"].sort_values("data").head(5)[
    ["rodada", "adversario", "mando", "gols_pro", "gols_contra", "resultado", "pontos"]
]
# %%
tabela = longo.groupby("time").agg(J=("id_jogo", "count"), P=("pontos", "sum"))
tabela.loc[["Vila Nova FC", "Atlético Goianiense", "Goiás"]]
# %%
longo = longo.sort_values(["time", "rodada", "data"]).reset_index(drop=True)
longo["pontos_acumulados"] = longo.groupby("time")["pontos"].cumsum()

longo[longo["time"] == "Vila Nova FC"][["rodada", "adversario", "pontos", "pontos_acumulados"]].head(6)
# %%
longo.groupby("time")["pontos_acumulados"].max().loc[["Vila Nova FC", "Atlético Goianiense", "Goiás"]]

# %%
Path("data/processed").mkdir(parents=True, exist_ok=True)
longo.to_csv("data/processed/jogos_longo.csv", index=False, encoding="utf-8-sig")
print("salvo:", len(longo), "linhas")
# %%
vila = longo[longo["time"] == "Vila Nova FC"]

print(vila["resultado"].value_counts())
print()
print(vila.groupby("mando").agg(
    jogos=("id_jogo", "count"),
    pontos=("pontos", "sum"),
    gols_pro=("gols_pro", "sum"),
    gols_contra=("gols_contra", "sum"),
))
print()
print(vila[["gols_pro_1t", "gols_pro_2t"]].sum())
# %%
tres = longo[longo["time"].isin(["Vila Nova FC", "Atlético Goianiense", "Goiás"])]

resumo = tres.groupby("time").agg(
    jogos=("id_jogo", "count"),
    pontos=("pontos", "sum"),
    gols_pro=("gols_pro", "sum"),
    gols_contra=("gols_contra", "sum"),
    gols_1t=("gols_pro_1t", "sum"),
    gols_2t=("gols_pro_2t", "sum"),
)
resumo["aproveitamento_%"] = (resumo.pontos / (resumo.jogos * 3) * 100).round(1)
resumo["gols_2t_%"] = (resumo.gols_2t / resumo.gols_pro * 100).round(1)
print(resumo)

print()
print((tres.pivot_table(index="time", columns="mando", values="pontos", aggfunc="mean") / 3 * 100).round(1))
# %%
