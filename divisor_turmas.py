import math
import json
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os

def carregar_e_ordenar_alunos(caminho_excel):
    df = pd.read_excel(caminho_excel)
    
    df['RTP'] = df['RTP'].fillna(0).astype(int)
    df['Mau_Comportamento'] = df['Mau_Comportamento'].fillna(0).astype(int)
    df['QE'] = df['QE'].fillna(0).astype(int)
    df['QV'] = df['QV'].fillna(0).astype(int) 
    
    df['Agrupar_Com_Pais'] = df['Agrupar_Com_Pais'].fillna("").astype(str)
    df['Separar_De_Pais'] = df['Separar_De_Pais'].fillna("").astype(str)
    df['Agrupar_Com_Professores'] = df['Agrupar_Com_Professores'].fillna("").astype(str)
    df['Separar_De_Professores'] = df['Separar_De_Professores'].fillna("").astype(str)
    df['Turma_Origem'] = df['Turma_Origem'].fillna("Desconhecida").astype(str)
    
    if 'Artes' not in df.columns:
        df['Artes'] = "Música"
    df['Artes'] = df['Artes'].fillna("Música").astype(str)
    df['Sexo'] = df['Sexo'].fillna("").astype(str).str.upper()
    
    df = df.sort_values(by=['RTP', 'Mau_Comportamento', 'QE', 'QV', 'Sexo'], ascending=[False, False, False, False, True]).reset_index(drop=True)
    return df

def distribuir_turmas(df, max_por_turma=30, limite_excecao=31, max_por_genero=20):
    nomes_turmas = ["7.º A", "7.º B", "7.º C", "7.º D", "7.º E", "7.º F", "7.º G", "7.º H"]
    num_total_turmas = len(nomes_turmas)
    turmas = {nome: [] for nome in nomes_turmas}
    
    total_alunos = len(df)
    media_ideal_alunos = total_alunos / num_total_turmas
    total_espanhol = len(df[df['Lingua'].str.lower() == 'espanhol'])
    
    turma_mista = None
    num_turmas_espanhol = 0
    
    for k in range(1, num_total_turmas):
        if k == 0: continue
        tamanho_medio = total_espanhol / k
        if 25 <= tamanho_medio <= max_por_turma:
            num_turmas_espanhol = k
            turma_mista = None
            break
            
    if num_turmas_espanhol == 0:
        num_turmas_espanhol = math.ceil(total_espanhol / media_ideal_alunos)
        turmas_espanhol = list(reversed(nomes_turmas))[:num_turmas_espanhol]
        turma_mista = turmas_espanhol[-1]
        vagas_espanhol_na_mista = total_espanhol % math.floor(media_ideal_alunos)
        if vagas_espanhol_na_mista == 0 and total_espanhol > 0:
            vagas_espanhol_na_mista = math.floor(media_ideal_alunos)
    else:
        turmas_espanhol = list(reversed(nomes_turmas))[:num_turmas_espanhol]
        vagas_espanhol_na_mista = 0

    turmas_exclusivas_frances = [t for t in nomes_turmas if t not in turmas_espanhol]
    alunos_processados = set()
    lista_alunos = df.to_dict('records')

    # ====================================================================
    # PRÉ-PROCESSAMENTO: LIMPEZA DE CONFLITOS DE IDIOMA DA PIPELINE
    # ====================================================================
    for aluno in lista_alunos:
        aluno['Agrupar_Com_Pais_Orig'] = aluno['Agrupar_Com_Pais']
        aluno['Agrupar_Com_Professores_Orig'] = aluno['Agrupar_Com_Professores']
        
        # Filtro Pais
        pedidos_pais_limpos = []
        for p in [n.strip() for n in aluno['Agrupar_Com_Pais'].split(',') if n.strip()]:
            alvo = next((x for x in lista_alunos if x['Nome'].lower() == p.lower()), None)
            if alvo and alvo['Lingua'].lower() != aluno['Lingua'].lower():
                print(f"⚠️ FILTRO PIPELINE: Pedido de {aluno['Nome']} para agrupar com {alvo['Nome']} foi removido (Conflito de Idioma).")
            else:
                pedidos_pais_limpos.append(p)
        aluno['Agrupar_Com_Pais'] = ", ".join(pedidos_pais_limpos)

        # Filtro Professores
        pedidos_prof_limpos = []
        for p in [n.strip() for n in aluno['Agrupar_Com_Professores'].split(',') if n.strip()]:
            alvo = next((x for x in lista_alunos if x['Nome'].lower() == p.lower()), None)
            if alvo and alvo['Lingua'].lower() != aluno['Lingua'].lower():
                pass # Remove da pipeline
            else:
                pedidos_prof_limpos.append(p)
        aluno['Agrupar_Com_Professores'] = ", ".join(pedidos_prof_limpos)

    # Função Barreira de Género
    def respeita_limite_genero(lista_turma):
        m = sum(1 for x in lista_turma if x['Sexo'] == 'M')
        f = sum(1 for x in lista_turma if x['Sexo'] == 'F')
        return m <= max_por_genero and f <= max_por_genero

    def pode_ficar_na_turma_imperativo(aluno, lista_turma):
        vetos_pais_aluno = [n.strip().lower() for n in aluno['Separar_De_Pais'].split(',') if n.strip()]
        for integrante in lista_turma:
            nome_int = integrante['Nome'].lower()
            if nome_int in vetos_pais_aluno: return False
            vetos_pais_int = [n.strip().lower() for n in integrante['Separar_De_Pais'].split(',') if n.strip()]
            if aluno['Nome'].lower() in vetos_pais_int: return False
        return True

    def avaliar_sugestoes_professores(aluno, lista_turma):
        score = 0
        vetos_prof_aluno = [n.strip().lower() for n in aluno['Separar_De_Professores'].split(',') if n.strip()]
        pedidos_prof_aluno = [n.strip().lower() for n in aluno['Agrupar_Com_Professores'].split(',') if n.strip()]
        for integrante in lista_turma:
            nome_int = integrante['Nome'].lower()
            if nome_int in vetos_prof_aluno: score += 1
            if nome_int in pedidos_prof_aluno: score -= 1
            vetos_prof_int = [n.strip().lower() for n in integrante['Separar_De_Professores'].split(',') if n.strip()]
            pedidos_prof_int = [n.strip().lower() for n in integrante['Agrupar_Com_Professores'].split(',') if n.strip()]
            if aluno['Nome'].lower() in vetos_prof_int: score += 1
            if aluno['Nome'].lower() in pedidos_prof_int: score -= 1
        return score

    def obter_turmas_elegiveis_individual(aluno_obj, limite_tamanho):
        lingua_aluno = aluno_obj['Lingua'].lower()
        sexo_aluno = aluno_obj['Sexo']
        elegiveis = []
        
        for t in nomes_turmas:
            contagem = turmas[t]
            if len(contagem) + 1 > limite_tamanho: continue
            
            # Bloqueio de Lotação de Género (Máximo 20)
            if sexo_aluno == 'M' and sum(1 for x in contagem if x['Sexo'] == 'M') >= max_por_genero: continue
            if sexo_aluno == 'F' and sum(1 for x in contagem if x['Sexo'] == 'F') >= max_por_genero: continue
            
            esp_na_turma = sum(1 for x in contagem if x['Lingua'].lower() == 'espanhol')
            fra_na_turma = sum(1 for x in contagem if x['Lingua'].lower() == 'francês')
            
            if lingua_aluno == 'espanhol':
                if t in turmas_exclusivas_frances: continue
                if t == turma_mista and esp_na_turma + 1 > vagas_espanhol_na_mista and limite_tamanho <= max_por_turma: continue
                elegiveis.append(t)
            else:
                if t in turmas_espanhol and t != turma_mista: continue
                if t == turma_mista and fra_na_turma + 1 > (media_ideal_alunos - vagas_espanhol_na_mista) and limite_tamanho <= max_por_turma: continue
                elegiveis.append(t)
                
        return elegiveis

    def taxa(t, lingua, feature):
        count = sum(1 for x in turmas[t] if x[feature] == 1 and x['Lingua'].lower() == lingua)
        if lingua == 'espanhol':
            cap = vagas_espanhol_na_mista if t == turma_mista else media_ideal_alunos
        else:
            cap = (media_ideal_alunos - vagas_espanhol_na_mista) if t == turma_mista else media_ideal_alunos
        return count / cap if cap > 0 else 0

    def tentar_alocar_grupo(grupo_total, misto, limite_tamanho):
        if misto:
            if turma_mista:
                contagem = turmas[turma_mista]
                esp_na_mista = sum(1 for x in contagem if x['Lingua'].lower() == 'espanhol')
                fra_na_mista = sum(1 for x in contagem if x['Lingua'].lower() == 'francês')
                num_esp_g = sum(1 for x in grupo_total if x['Lingua'].lower() == 'espanhol')
                num_fra_g = sum(1 for x in grupo_total if x['Lingua'].lower() == 'francês')
                
                condicao_vagas = True
                if limite_tamanho <= max_por_turma:
                    condicao_vagas = (esp_na_mista + num_esp_g <= vagas_espanhol_na_mista and
                                      fra_na_mista + num_fra_g <= (media_ideal_alunos - vagas_espanhol_na_mista))
                
                temp_turma = contagem + grupo_total
                if len(contagem) + len(grupo_total) <= limite_tamanho and condicao_vagas:
                    if respeita_limite_genero(temp_turma) and all(pode_ficar_na_turma_imperativo(m, contagem) for m in grupo_total):
                        for membro in grupo_total:
                            turmas[turma_mista].append(membro)
                            alunos_processados.add(membro['Nome'])
                        return True
            return False
        else:
            lingua_comum = grupo_total[0]['Lingua'].lower()
            turmas_elegiveis = []
            for t in nomes_turmas:
                contagem = turmas[t]
                if len(contagem) + len(grupo_total) > limite_tamanho: continue
                
                if not respeita_limite_genero(contagem + grupo_total): continue # Filtro de Género para Grupos
                
                esp_na_turma = sum(1 for x in contagem if x['Lingua'].lower() == 'espanhol')
                fra_na_turma = sum(1 for x in contagem if x['Lingua'].lower() == 'francês')
                
                if lingua_comum == 'espanhol':
                    if t in turmas_espanhol:
                        if t == turma_mista and limite_tamanho <= max_por_turma and esp_na_turma + len(grupo_total) > vagas_espanhol_na_mista: continue
                        turmas_elegiveis.append(t)
                else:
                    if t in turmas_espanhol and t != turma_mista: continue
                    if t == turma_mista and limite_tamanho <= max_por_turma and fra_na_turma + len(grupo_total) > (media_ideal_alunos - vagas_espanhol_na_mista): continue
                    turmas_elegiveis.append(t)

            if not turmas_elegiveis: return False
            
            turmas_validas = [t for t in turmas_elegiveis if all(pode_ficar_na_turma_imperativo(m, turmas[t]) for m in grupo_total)]
            if not turmas_validas: 
                turmas_validas = turmas_elegiveis
            
            def avaliar_turma_grupo(t):
                score_rtp = sum(1 for x in turmas[t] if x['RTP'] == 1) if any(g['RTP'] == 1 for g in grupo_total) else 0
                score_mau = sum(1 for x in turmas[t] if x['Mau_Comportamento'] == 1) if any(g['Mau_Comportamento'] == 1 for g in grupo_total) else 0
                score_qe = sum(1 for x in turmas[t] if x['QE'] == 1) if any(g['QE'] == 1 for g in grupo_total) else 0
                origem_count = sum(1 for x in turmas[t] for g in grupo_total if x['Turma_Origem'] == g['Turma_Origem'])
                score_prof = sum(avaliar_sugestoes_professores(g, turmas[t]) for g in grupo_total)
                score_qv = sum(1 for x in turmas[t] if x['QV'] == 1) if any(g['QV'] == 1 for g in grupo_total) else 0 
                score_artes = sum(1 for x in turmas[t] if x['Artes'].lower() == grupo_total[0]['Artes'].lower())
                return (score_rtp, score_mau, score_qe, origem_count, score_prof, score_qv, score_artes, len(turmas[t]))

            turma_destino = min(turmas_validas, key=avaliar_turma_grupo)
            for membro in grupo_total:
                turmas[turma_destino].append(membro)
                alunos_processados.add(membro['Nome'])
            return True

    def alocar_grupo(grupo_total, misto):
        if not tentar_alocar_grupo(grupo_total, misto, max_por_turma):
            tentar_alocar_grupo(grupo_total, misto, limite_excecao)

    def alocar_individual(aluno):
        turmas_elegiveis = obter_turmas_elegiveis_individual(aluno, max_por_turma)
        if not turmas_elegiveis:
            turmas_elegiveis = obter_turmas_elegiveis_individual(aluno, limite_excecao)
            
        if not turmas_elegiveis:
            # Em último caso absoluto (se houver mais de 160 rapazes não há matemática que salve), força entrada
            if aluno['Lingua'].lower() == 'espanhol': turmas_elegiveis = turmas_espanhol
            else: turmas_elegiveis = turmas_exclusivas_frances

        def key_individual(t):
            return (
                taxa(t, aluno['Lingua'].lower(), 'RTP') if aluno['RTP'] == 1 else 0,
                taxa(t, aluno['Lingua'].lower(), 'Mau_Comportamento') if aluno['Mau_Comportamento'] == 1 else 0,
                taxa(t, aluno['Lingua'].lower(), 'QE') if aluno['QE'] == 1 else 0,
                sum(1 for x in turmas[t] if x['Turma_Origem'] == aluno['Turma_Origem']),
                avaliar_sugestoes_professores(aluno, turmas[t]),
                taxa(t, aluno['Lingua'].lower(), 'QV') if aluno['QV'] == 1 else 0, 
                sum(1 for x in turmas[t] if x['Artes'].lower() == aluno['Artes'].lower()),
                sum(1 for x in turmas[t] if x['Sexo'] == aluno['Sexo']),
                len(turmas[t])
            )

        turma_destino = min(turmas_elegiveis, key=key_individual)
        if not pode_ficar_na_turma_imperativo(aluno, turmas[turma_destino]):
            alternativas = [t for t in turmas_elegiveis if t != turma_destino and pode_ficar_na_turma_imperativo(aluno, turmas[t])]
            if alternativas: turma_destino = min(alternativas, key=key_individual)

        turmas[turma_destino].append(aluno)
        alunos_processados.add(aluno['Nome'])

    componentes = {a['Nome'].lower(): [a] for a in lista_alunos}
    parent = {a['Nome'].lower(): a['Nome'].lower() for a in lista_alunos}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def merge(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            novo_grupo = componentes[ra] + componentes[rb]
            if len(novo_grupo) > limite_excecao: return False
            nomes_novo = {m['Nome'].lower() for m in novo_grupo}
            for m in novo_grupo:
                vetos = {v.strip().lower() for v in m['Separar_De_Pais'].split(',') if v.strip()}
                if vetos & nomes_novo: return False
            
            parent[rb] = ra
            componentes[ra] = novo_grupo
            del componentes[rb]
            return True
        return False

    for aluno in lista_alunos:
        nome_a = aluno['Nome'].lower()
        pedidos_a = [n.strip().lower() for n in aluno['Agrupar_Com_Pais'].split(',') if n.strip()]
        for p in pedidos_a:
            aluno_p = next((x for x in lista_alunos if x['Nome'].lower() == p), None)
            if aluno_p:
                pedidos_p = [n.strip().lower() for n in aluno_p['Agrupar_Com_Pais'].split(',') if n.strip()]
                if nome_a in pedidos_p:
                    merge(nome_a, p)

    for aluno in lista_alunos:
        nome_a = aluno['Nome'].lower()
        pedidos_a = [n.strip().lower() for n in aluno['Agrupar_Com_Pais'].split(',') if n.strip()]
        if len(pedidos_a) == 1:
            p = pedidos_a[0]
            if p in parent: merge(nome_a, p)

    for aluno in lista_alunos:
        nome_a = aluno['Nome'].lower()
        pedidos_a = [n.strip().lower() for n in aluno['Agrupar_Com_Pais'].split(',') if n.strip()]
        if len(pedidos_a) <= 1: continue 

        ra = find(nome_a)
        nomes_no_grupo = {m['Nome'].lower() for m in componentes[ra]}
        if any(p in nomes_no_grupo for p in pedidos_a): continue
            
        for p in pedidos_a:
            if p in parent and merge(nome_a, p): break

    grupos_de_pedidos_limpos = [g for g in componentes.values() if len(g) > 1]
    grupos_rtp_alta, grupos_rtp_baixa = [], []
    grupos_normais_alta, grupos_normais_baixa = [], []

    for grupo_total in grupos_de_pedidos_limpos:
        linguas_grupo = set(x['Lingua'].lower() for x in grupo_total)
        tem_rtp = any(x['RTP'] == 1 for x in grupo_total)
        misto = ('espanhol' in linguas_grupo and 'francês' in linguas_grupo)

        if tem_rtp:
            if misto: grupos_rtp_baixa.append(grupo_total)
            else: grupos_rtp_alta.append(grupo_total)
        else:
            if misto: grupos_normais_baixa.append(grupo_total)
            else: grupos_normais_alta.append(grupo_total)

    for lista_g in (grupos_rtp_alta, grupos_rtp_baixa, grupos_normais_alta, grupos_normais_baixa):
        lista_g.sort(key=len, reverse=True)

    for g in grupos_rtp_alta: alocar_grupo(g, misto=False)
    for g in grupos_rtp_baixa: alocar_grupo(g, misto=True)

    for aluno in lista_alunos:
        if aluno['Nome'] in alunos_processados: continue
        if aluno['RTP'] == 1: alocar_individual(aluno)

    for g in grupos_normais_alta: alocar_grupo(g, misto=False)
    for g in grupos_normais_baixa: alocar_grupo(g, misto=True)

    for aluno in lista_alunos:
        if aluno['Nome'] in alunos_processados: continue
        alocar_individual(aluno)

    def obter_mapeamento_atual():
        return {alu['Nome'].lower(): t_nome for t_nome, lista in turmas.items() for alu in lista}

    def alunos_satisfeitos(lista_turma):
        nomes_turma = {x['Nome'].lower() for x in lista_turma}
        satisfeitos = set()
        for x in lista_turma:
            pedidos = [p.strip().lower() for p in x['Agrupar_Com_Pais_Orig'].split(',') if p.strip()]
            if any(p in nomes_turma for p in pedidos):
                satisfeitos.add(x['Nome'].lower())
        return satisfeitos

    lista_alunos_opt = sorted(lista_alunos, key=lambda x: len([n for n in x['Agrupar_Com_Pais'].split(',') if n.strip()]))

    for iteracao in range(15):
        aluno_turma = obter_mapeamento_atual()
        troca_feita_nesta_iteracao = False
        
        for aluno in lista_alunos_opt:
            nome_aluno_l = aluno['Nome'].lower()
            if aluno['Agrupar_Com_Pais'] == "" or nome_aluno_l not in aluno_turma: continue
                
            parceiros = [n.strip() for n in aluno['Agrupar_Com_Pais'].split(',') if n.strip()]
            if any(p.lower() in aluno_turma and aluno_turma[p.lower()] == aluno_turma[nome_aluno_l] for p in parceiros):
                continue
            
            for par_nome in parceiros:
                par_l = par_nome.lower()
                if par_l not in aluno_turma: continue
                
                turma_atual = aluno_turma[nome_aluno_l]
                turma_alvo = aluno_turma[par_l]
                if turma_atual == turma_alvo: continue
                
                lingua_aluno = aluno['Lingua'].lower()
                candidato_troca = None
                
                sat_atual_antes = alunos_satisfeitos(turmas[turma_atual])
                sat_alvo_antes = alunos_satisfeitos(turmas[turma_alvo])
                
                for potencial in turmas[turma_alvo]:
                    if (potencial['RTP'] == 0 and 
                        potencial['Mau_Comportamento'] == 0 and 
                        potencial['Lingua'].lower() == lingua_aluno):
                        
                        temp_atual = [x for x in turmas[turma_atual] if x['Nome'] != aluno['Nome']] + [potencial]
                        temp_alvo = [x for x in turmas[turma_alvo] if x['Nome'] != potencial['Nome']] + [aluno]
                        
                        if not respeita_limite_genero(temp_atual) or not respeita_limite_genero(temp_alvo): continue
                        if not sat_atual_antes.issubset(alunos_satisfeitos(temp_atual)): continue
                        if not sat_alvo_antes.issubset(alunos_satisfeitos(temp_alvo)): continue
                        
                        if (pode_ficar_na_turma_imperativo(aluno, temp_alvo) and pode_ficar_na_turma_imperativo(potencial, temp_atual) and
                            avaliar_sugestoes_professores(aluno, temp_alvo) <= 0 and avaliar_sugestoes_professores(potencial, temp_atual) <= 0):
                            candidato_troca = potencial
                            break
                
                if not candidato_troca:
                    for potencial in turmas[turma_alvo]:
                        if (potencial['RTP'] <= aluno['RTP'] and 
                            potencial['Mau_Comportamento'] <= aluno['Mau_Comportamento'] and
                            potencial['Lingua'].lower() == lingua_aluno):
                            
                            temp_atual = [x for x in turmas[turma_atual] if x['Nome'] != aluno['Nome']] + [potencial]
                            temp_alvo = [x for x in turmas[turma_alvo] if x['Nome'] != potencial['Nome']] + [aluno]
                            
                            if not respeita_limite_genero(temp_atual) or not respeita_limite_genero(temp_alvo): continue
                            if not sat_atual_antes.issubset(alunos_satisfeitos(temp_atual)): continue
                            if not sat_alvo_antes.issubset(alunos_satisfeitos(temp_alvo)): continue
                                
                            if pode_ficar_na_turma_imperativo(aluno, temp_alvo) and pode_ficar_na_turma_imperativo(potencial, temp_atual):
                                candidato_troca = potencial
                                break

                if candidato_troca:
                    turmas[turma_atual].remove(aluno)
                    turmas[turma_alvo].remove(candidato_troca)
                    turmas[turma_alvo].append(aluno)
                    turmas[turma_atual].append(candidato_troca)
                    troca_feita_nesta_iteracao = True
                    aluno_turma = obter_mapeamento_atual()
                    break 
                
        if not troca_feita_nesta_iteracao:
            break

    def balancear_caracteristica(feature):
        for _ in range(20):
            contagens = {t: sum(1 for a in turmas[t] if a[feature] == 1) for t in nomes_turmas}
            max_t = max(contagens, key=contagens.get)
            min_t = min(contagens, key=contagens.get)
            if contagens[max_t] - contagens[min_t] <= 1: break 
            troca_feita = False
            for mau_aluno in turmas[max_t]:
                if mau_aluno[feature] == 1:
                    sat_max_antes = alunos_satisfeitos(turmas[max_t])
                    for bom_aluno in turmas[min_t]:
                        if bom_aluno[feature] == 0 and bom_aluno['Lingua'].lower() == mau_aluno['Lingua'].lower():
                            sat_min_antes = alunos_satisfeitos(turmas[min_t])
                            temp_max = [x for x in turmas[max_t] if x['Nome'] != mau_aluno['Nome']] + [bom_aluno]
                            temp_min = [x for x in turmas[min_t] if x['Nome'] != bom_aluno['Nome']] + [mau_aluno]
                            
                            if not respeita_limite_genero(temp_max) or not respeita_limite_genero(temp_min): continue
                            if not sat_max_antes.issubset(alunos_satisfeitos(temp_max)): continue
                            if not sat_min_antes.issubset(alunos_satisfeitos(temp_min)): continue

                            if pode_ficar_na_turma_imperativo(mau_aluno, temp_min) and pode_ficar_na_turma_imperativo(bom_aluno, temp_max):
                                turmas[max_t].remove(mau_aluno)
                                turmas[min_t].remove(bom_aluno)
                                turmas[min_t].append(mau_aluno)
                                turmas[max_t].append(bom_aluno)
                                troca_feita = True
                                break
                    if troca_feita: break
            if not troca_feita: break

    def balancear_genero():
        for _ in range(40):
            contagens_M = {t: sum(1 for a in turmas[t] if a['Sexo'] == 'M') for t in nomes_turmas}
            max_t = max(contagens_M, key=contagens_M.get)
            min_t = min(contagens_M, key=contagens_M.get)
            if contagens_M[max_t] - contagens_M[min_t] <= 1: break 
            troca_feita = False
            for rapaz in turmas[max_t]:
                if rapaz['Sexo'] == 'M':
                    sat_max_antes = alunos_satisfeitos(turmas[max_t])
                    for rapariga in turmas[min_t]:
                        if rapariga['Sexo'] == 'F' and rapariga['Lingua'].lower() == rapaz['Lingua'].lower():
                            if rapaz['RTP'] == rapariga['RTP'] and rapaz['Mau_Comportamento'] == rapariga['Mau_Comportamento']:
                                sat_min_antes = alunos_satisfeitos(turmas[min_t])
                                temp_max = [x for x in turmas[max_t] if x['Nome'] != rapaz['Nome']] + [rapariga]
                                temp_min = [x for x in turmas[min_t] if x['Nome'] != rapariga['Nome']] + [rapaz]
                                
                                if not respeita_limite_genero(temp_max) or not respeita_limite_genero(temp_min): continue
                                if not sat_max_antes.issubset(alunos_satisfeitos(temp_max)): continue
                                if not sat_min_antes.issubset(alunos_satisfeitos(temp_min)): continue

                                if pode_ficar_na_turma_imperativo(rapaz, temp_min) and pode_ficar_na_turma_imperativo(rapariga, temp_max):
                                    turmas[max_t].remove(rapaz)
                                    turmas[min_t].remove(rapariga)
                                    turmas[min_t].append(rapaz)
                                    turmas[max_t].append(rapariga)
                                    troca_feita = True
                                    break
                    if troca_feita: break
            if not troca_feita: break

    balancear_caracteristica('RTP')
    balancear_caracteristica('Mau_Comportamento')
    balancear_caracteristica('QE')
    balancear_caracteristica('QV')
    balancear_genero()

    return turmas

def diagnosticar_falha(turmas, aluno_obj, alvo_obj, t_atual, t_alvo):
    v_aluno = [v.strip().lower() for v in str(aluno_obj.get('Separar_De_Pais', '')).split(',') if v.strip()]
    v_alvo = [v.strip().lower() for v in str(alvo_obj.get('Separar_De_Pais', '')).split(',') if v.strip()]
    n_aluno_l = aluno_obj['Nome'].lower()
    n_alvo_l = alvo_obj['Nome'].lower()
    
    if n_alvo_l in v_aluno or n_aluno_l in v_alvo:
        return f"Paradoxo: Pedido conflitante dos pais para juntar e separar '{alvo_obj['Nome']}' em simultâneo."
    if aluno_obj['Lingua'].lower() != alvo_obj['Lingua'].lower():
        return f"Conflito de Idioma: '{alvo_obj['Nome']}' estuda {alvo_obj['Lingua']}. O pedido foi retirado do processamento automático."
        
    for a_turma in turmas.get(t_alvo, []):
        if a_turma['Nome'].lower() in v_aluno:
            return f"Veto Direto: Pediu para se afastar de '{a_turma['Nome']}', que já está na turma alvo ({t_alvo})."
        v_terceiro = [v.strip().lower() for v in str(a_turma.get('Separar_De_Pais', '')).split(',') if v.strip()]
        if n_aluno_l in v_terceiro:
            return f"Veto Recebido: O aluno '{a_turma['Nome']}' (na {t_alvo}) tem um pedido imperativo para se afastar deste aluno."
            
    for a_turma in turmas.get(t_atual, []):
        if a_turma['Nome'].lower() in v_alvo:
            return f"Veto Inverso: O alvo '{alvo_obj['Nome']}' pediu para se afastar de '{a_turma['Nome']}', que está na turma atual ({t_atual})."
        v_terceiro = [v.strip().lower() for v in str(a_turma.get('Separar_De_Pais', '')).split(',') if v.strip()]
        if n_alvo_l in v_terceiro:
            return f"Veto Interno: '{alvo_obj['Nome']}' não pôde vir para a {t_atual} porque '{a_turma['Nome']}' bloqueou a sua entrada."
            
    return f"Limite rígido de Lotação (Máx: 30/31) ou Limite Rígido de Género (Máx: 20) atingido na turma de destino."

def exportar_resultados(turmas, df_original, ficheiro_saida="turmas_finais.xlsx"):
    writer = pd.ExcelWriter(ficheiro_saida, engine='openpyxl')
    resumo_dados = []
    
    aluno_turma = {}
    todos_alunos = []
    aluno_dit = {} 
    
    origens_unicas = sorted(df_original['Turma_Origem'].unique())
    
    for nome_turma in sorted(turmas.keys()):
        alunos = turmas[nome_turma]
        df_turma = pd.DataFrame(alunos)
        
        for aluno in alunos:
            aluno_turma[aluno['Nome'].lower()] = nome_turma
            todos_alunos.append(aluno)
            aluno_dit[aluno['Nome'].lower()] = aluno
        
        if not df_turma.empty:
            df_salvar = df_turma.drop(columns=['Prioridade', 'Agrupar_Com_Pais_Orig', 'Agrupar_Com_Professores_Orig'], errors='ignore')
            if 'Nome' in df_salvar.columns:
                df_salvar = df_salvar.sort_values(by='Nome')
            df_salvar.to_excel(writer, sheet_name=nome_turma, index=False)
            
            estatisticas_turma = {
                "Turma": nome_turma,
                "Total Alunos": len(df_turma),
                "Rapazes (M)": len(df_turma[df_turma['Sexo'].str.upper() == 'M']),
                "Raparigas (F)": len(df_turma[df_turma['Sexo'].str.upper() == 'F']),
                "Espanhol": len(df_turma[df_turma['Lingua'].str.lower() == 'espanhol']),
                "Francês": len(df_turma[df_turma['Lingua'].str.lower() == 'francês']),
                "RTP": df_turma['RTP'].sum(),
                "Mau Comp.": df_turma['Mau_Comportamento'].sum(),
                "Q. Excelência": df_turma['QE'].sum(),
                "Q. Valor": df_turma['QV'].sum()
            }
            
            for org in origens_unicas:
                estatisticas_turma[f"Vindos do {org}"] = len(df_turma[df_turma['Turma_Origem'] == org])
                
            resumo_dados.append(estatisticas_turma)
            
    df_resumo = pd.DataFrame(resumo_dados)
    df_resumo.to_excel(writer, sheet_name="Resumo Estatístico", index=False)

    validacoes = []
    for aluno in todos_alunos:
        nome_aluno = aluno['Nome']
        nome_aluno_lower = nome_aluno.lower()
        turma_atual = aluno_turma.get(nome_aluno_lower, "")
        
        # Validar usando as strings Originais de Excel, mesmo os que foram cortados da pipeline
        if str(aluno.get('Agrupar_Com_Pais_Orig', '')) not in ["", "nan", "None"]:
            parceiros = [n.strip() for n in str(aluno.get('Agrupar_Com_Pais_Orig', '')).split(',') if n.strip()]
            parceiros_na_turma = [p for p in parceiros if p.lower() in aluno_turma and aluno_turma[p.lower()] == turma_atual]
            
            if parceiros_na_turma:
                status = "✅ Cumprido"
                alvo_str = " OU ".join(parceiros)
                motivo = f"Ficou colocado com sucesso na mesma turma que: {', '.join(parceiros_na_turma)}"
            else:
                status = "❌ Falhou Crítico"
                alvo_str = " OU ".join(parceiros)
                motivos_especificos = []
                for p in parceiros:
                    if p.lower() in aluno_dit:
                        alvo_completo = aluno_dit[p.lower()]
                        turma_alvo = aluno_turma.get(p.lower(), "")
                        razao = diagnosticar_falha(turmas, aluno, alvo_completo, turma_atual, turma_alvo)
                        motivos_especificos.append(f"-> Com '{alvo_completo['Nome']}': {razao}")
                    else:
                        motivos_especificos.append(f"-> Com '{p}': Aluno não existe na base de dados.")
                motivo = "\n".join(motivos_especificos)
                
            validacoes.append({"Aluno": nome_aluno, "Tipo Pedido": "Agrupar (Pais)", "Alvo": alvo_str, "Turma Aluno": turma_atual, "Turma Alvo": "-", "Estado": status, "Motivo Falha": motivo})
        
        if str(aluno.get('Separar_De_Pais', '')) not in ["", "nan", "None"]:
            vetos = [n.strip() for n in str(aluno['Separar_De_Pais']).split(',') if n.strip()]
            for v in vetos:
                v_lower = v.lower()
                if v_lower in aluno_turma:
                    turma_alvo = aluno_turma[v_lower]
                    status = "✅ Cumprido" if turma_atual != turma_alvo else "❌ Falhou Crítico"
                    motivo = "-" if status.startswith("✅") else "Falha catastrófica de processamento (Limite imperativo violado)."
                    validacoes.append({"Aluno": nome_aluno, "Tipo Pedido": "Separar (Pais)", "Alvo": v, "Turma Aluno": turma_atual, "Turma Alvo": turma_alvo, "Estado": status, "Motivo Falha": motivo})

        if str(aluno.get('Agrupar_Com_Professores_Orig', '')) not in ["", "nan", "None"]:
            pedidos_prof = [n.strip() for n in str(aluno['Agrupar_Com_Professores_Orig']).split(',') if n.strip()]
            for p in pedidos_prof:
                p_lower = p.lower()
                if p_lower in aluno_turma:
                    turma_alvo = aluno_turma[p_lower]
                    status = "✅ Cumprido" if turma_atual == turma_alvo else "⚠️ Ignorado (Sugestão)"
                    motivo = "-" if status.startswith("✅") else "A sugestão do professor cedeu perante o filtro de idioma ou a distribuição estatística."
                    validacoes.append({"Aluno": nome_aluno, "Tipo Pedido": "Agrupar (Prof)", "Alvo": p, "Turma Aluno": turma_atual, "Turma Alvo": turma_alvo, "Estado": status, "Motivo Falha": motivo})

        if str(aluno.get('Separar_De_Professores', '')) not in ["", "nan", "None"]:
            vetos_prof = [n.strip() for n in str(aluno['Separar_De_Professores']).split(',') if n.strip()]
            for v in vetos_prof:
                v_lower = v.lower()
                if v_lower in aluno_turma:
                    turma_alvo = aluno_turma[v_lower]
                    status = "✅ Cumprido" if turma_atual != turma_alvo else "⚠️ Ignorado (Sugestão)"
                    motivo = "-" if status.startswith("✅") else "A sugestão de separação foi sacrificada para não quebrar limites ou equilibrar outras variáveis (RTP, Mau Comportamento, QE, etc.)."
                    validacoes.append({"Aluno": nome_aluno, "Tipo Pedido": "Separar (Prof)", "Alvo": v, "Turma Aluno": turma_atual, "Turma Alvo": turma_alvo, "Estado": status, "Motivo Falha": motivo})

    if validacoes:
        pd.DataFrame(validacoes).to_excel(writer, sheet_name="Validação de Pedidos", index=False)
    else:
        pd.DataFrame([{"Aviso": "Nenhum pedido registado."}]).to_excel(writer, sheet_name="Validação de Pedidos", index=False)

    writer.close()
    print(f"\nResultados guardados com sucesso no ficheiro '{ficheiro_saida}'.")

def gerar_mapa_visual(turmas, df_original, ficheiro_saida_html="mapa_turmas.html"):
    nodes = []
    edges = []
    aluno_turma = {}
    
    lista_alunos = df_original.to_dict('records')
    
    cores_turmas = {
        "7.º A": "#3498db", "7.º B": "#9b59b6", "7.º C": "#f1c40f", "7.º D": "#e67e22",
        "7.º E": "#1abc9c", "7.º F": "#34495e", "7.º G": "#e74c3c", "7.º H": "#2ecc71"
    }

    posicoes_turmas = {
        "7.º A": {"x": -400, "y": -400},
        "7.º B": {"x": 0,    "y": -500},
        "7.º C": {"x": 400,  "y": -400},
        "7.º D": {"x": 500,  "y": 0},
        "7.º E": {"x": 400,  "y": 400},
        "7.º F": {"x": 0,    "y": 500},
        "7.º G": {"x": -400, "y": 400},
        "7.º H": {"x": -500, "y": 0}
    }

    for turma_nome, alunos in turmas.items():
        pos_centro = posicoes_turmas.get(turma_nome, {"x": 0, "y": 0})
        alunos_ordenados = sorted(alunos, key=lambda x: x['Nome'])
        num_alunos = len(alunos_ordenados)
        
        for i, aluno in enumerate(alunos_ordenados):
            aluno_turma[aluno['Nome'].lower()] = turma_nome
            cor = cores_turmas.get(turma_nome, "#bdc3c7")
            
            angulo = (2 * math.pi * i) / num_alunos if num_alunos > 0 else 0
            raio_espalhamento = 80
            x_inicial = pos_centro["x"] + raio_espalhamento * math.cos(angulo)
            y_inicial = pos_centro["y"] + raio_espalhamento * math.sin(angulo)
            
            nodes.append({
                "id": aluno['Nome'].lower(),
                "label": aluno['Nome'],
                "group": turma_nome,
                "color": cor,
                "x": x_inicial,
                "y": y_inicial,
                "lingua": aluno.get('Lingua', '').lower(),
                "sexo": aluno.get('Sexo', '').upper(),
                "rtp": int(aluno.get('RTP', 0)),
                "mau": int(aluno.get('Mau_Comportamento', 0)),
                "qe": int(aluno.get('QE', 0)),
                "qv": int(aluno.get('QV', 0)),
                "origem": aluno.get('Turma_Origem', 'Desconhecida'),
                "artes": aluno.get('Artes', 'Música'),
                "pedidos_pais": aluno.get('Agrupar_Com_Pais', ''),
                "vetos_pais": aluno.get('Separar_De_Pais', ''),
                "pedidos_prof": aluno.get('Agrupar_Com_Professores', ''),
                "vetos_prof": aluno.get('Separar_De_Professores', ''),
                "title": f"Turma Atual: {turma_nome}<br>Origem: {aluno.get('Turma_Origem', '')}<br>Idioma: {aluno.get('Lingua', '')}<br>Género: {aluno.get('Sexo', '')}"
            })

    for aluno in lista_alunos:
        nome_l = aluno['Nome'].lower()
        if nome_l not in aluno_turma: continue

        pedidos = [n.strip().lower() for n in str(aluno.get('Agrupar_Com_Pais', '')).split(',') if n.strip()]
        for p in pedidos:
            if p in aluno_turma:
                edges.append({
                    "id": f"edge_{nome_l}_{p}", "from": nome_l, "to": p, 
                    "color": {"color": "#2ecc71", "highlight": "#27ae60"}, "arrows": "to", "type": "agrupar"
                })

        vetos = [n.strip().lower() for n in str(aluno.get('Separar_De_Pais', '')).split(',') if n.strip()]
        for v in vetos:
            if v in aluno_turma:
                edges.append({
                    "id": f"edge_{nome_l}_{v}", "from": nome_l, "to": v, 
                    "color": {"color": "#e74c3c", "highlight": "#c0392b"}, "dashes": True, "arrows": "to", "type": "separar"
                })

    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Painel Interativo de Gestão de Turmas - Constelações</title>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f5f6fa; overflow: hidden; }}
            #mynetwork {{ width: 100vw; height: calc(100vh - 70px); background-color: #ffffff; border-top: 1px solid #dcdde1; }}
            #control-panel {{ height: 70px; background-color: #2f3640; color: white; display: flex; align-items: center; padding: 0 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.15); z-index: 1000; position: relative; gap: 20px; }}
            .filter-group {{ display: flex; align-items: center; gap: 8px; font-size: 14px; }}
            select, button {{ padding: 8px 12px; border-radius: 4px; border: none; font-size: 14px; background-color: #f5f6fa; cursor: pointer; }}
            select:focus, button:focus {{ outline: none; }}
            button.btn-action {{ background-color: #4cd137; color: white; font-weight: bold; margin-left: auto; transition: background 0.2s; }}
            button.btn-action:hover {{ background-color: #44bd32; }}
            button.btn-danger {{ background-color: #e84118; color: white; font-weight: bold; }}
            button.btn-danger:hover {{ background-color: #c23616; }}
            #legend {{ position: absolute; bottom: 20px; left: 20px; background: rgba(255,255,255,0.95); padding: 15px; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-size: 13px; line-height: 1.8; z-index: 999; pointer-events: none; }}
            .sidebar {{ position: absolute; top: 90px; right: 20px; background: rgba(47, 54, 64, 0.95); color: white; padding: 20px; border-radius: 6px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); width: 280px; z-index: 999; display: none; }}
            .sidebar h3 {{ margin-top: 0; border-bottom: 1px solid #718093; padding-bottom: 8px; }}
        </style>
    </head>
    <body>
        <div id="control-panel">
            <div class="filter-group">
                <label>Idioma:</label>
                <select id="filter-lingua" onchange="aplicarFiltros()">
                    <option value="todos">Todos</option>
                    <option value="espanhol">Espanhol</option>
                    <option value="francês">Francês</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Género:</label>
                <select id="filter-sexo" onchange="aplicarFiltros()">
                    <option value="todos">Todos</option>
                    <option value="m">Rapazes (M)</option>
                    <option value="f">Raparigas (F)</option>
                </select>
            </div>
            <div class="filter-group">
                <label>Vulnerabilidade:</label>
                <select id="filter-vulnerabilidade" onchange="aplicarFiltros()">
                    <option value="todos">Todos</option>
                    <option value="rtp">Apenas RTP</option>
                    <option value="mau">Apenas Mau Comportamento</option>
                </select>
            </div>
            <button class="btn-danger" onclick="cortarTeiaSelecionada()">Cortar Ligação Selecionada</button>
            <button class="btn-action" onclick="exportarConfiguracaoManual()">Exportar Distribuição Final</button>
        </div>

        <div id="legend">
            <strong>Ilhas Separadas por Turma:</strong><br>
            <span style="color: #3498db;">● 7.º A</span> | <span style="color: #9b59b6;">● 7.º B</span> | <span style="color: #f1c40f;">● 7.º C</span> | <span style="color: #e67e22;">● 7.º D</span><br>
            <span style="color: #1abc9c;">● 7.º E</span> | <span style="color: #34495e;">● 7.º F</span> | <span style="color: #e74c3c;">● 7.º G</span> | <span style="color: #2ecc71;">● 7.º H</span><br>
            <hr style="border: 0; border-top: 1px solid #ccc; margin: 8px 0;">
            <strong>Análise da Teia Cruzada:</strong><br>
            • Os alunos começam agrupados no núcleo geográfico da sua própria turma.<br>
            • Qualquer linha inter-turmas representa um pedido que cruza fronteiras.<br>
            • Clica duas vezes num nó para transferir o aluno de ilha (turma) manualmente.
        </div>

        <div id="sidebar-edit" class="sidebar">
            <h3 id="edit-nome">Nome do Aluno</h3>
            <p id="edit-info"></p>
            <label for="edit-turma">Mover para a Turma:</label><br><br>
            <select id="edit-turma" style="width: 100%; background: white; color: black;"></select><br><br>
            <button class="btn-action" style="width: 100%; margin: 0;" onclick="confirmarMudancaTurma()">Confirmar Transferência</button>
        </div>

        <div id="mynetwork"></div>

        <script type="text/javascript">
            var rawNodes = {json.dumps(nodes)};
            var rawEdges = {json.dumps(edges)};
            
            var nodesDataset = new vis.DataSet(rawNodes);
            var edgesDataset = new vis.DataSet(rawEdges);
            
            var container = document.getElementById('mynetwork');
            var data = {{ nodes: nodesDataset, edges: edgesDataset }};
            
            var coresTurmas = {json.dumps(cores_turmas)};
            var posicoesCentrais = {json.dumps(posicoes_turmas)};
            
            var options = {{
                physics: {{
                    stabilization: true,
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {{ gravitationalConstant: -90, centralGravity: 0.01, springConstant: 0.05, springLength: 70, avoidOverlap: 1 }}
                }},
                nodes: {{ shape: 'dot', size: 15, font: {{ size: 12, face: 'Segoe UI' }}, borderWidth: 2 }},
                edges: {{ smooth: {{ type: 'continuous' }}, width: 2 }},
                interaction: {{ hover: true, selectConnectedEdges: false }}
            }};
            
            var network = new vis.Network(container, data, options);
            var alunoSelecionadoId = null;

            function aplicarFiltros() {{
                var fLingua = document.getElementById('filter-lingua').value;
                var fSexo = document.getElementById('filter-sexo').value;
                var fVuln = document.getElementById('filter-vulnerabilidade').value;

                rawNodes.forEach(function(node) {{
                    var visivel = true;
                    if (fLingua !== 'todos' && node.lingua !== fLingua) visivel = false;
                    if (fSexo !== 'todos' && node.sexo.toLowerCase() !== fSexo) visivel = false;
                    if (fVuln === 'rtp' && node.rtp !== 1) visivel = false;
                    if (fVuln === 'mau' && node.mau !== 1) visivel = false;

                    nodesDataset.update({{id: node.id, hidden: !visivel}});
                }});
            }}

            function cortarTeiaSelecionada() {{
                var selectedEdges = network.getSelectedEdges();
                if (selectedEdges.length > 0) {{
                    selectedEdges.forEach(function(edgeId) {{
                        edgesDataset.remove(edgeId);
                        rawEdges = rawEdges.filter(e => e.id !== edgeId);
                    }});
                    alert("A ligação selecionada foi eliminada da teia com sucesso!");
                }} else {{
                    alert("Por favor, clica primeiro numa das linhas para a selecionar.");
                }}
            }}

            network.on("doubleClick", function(params) {{
                if (params.nodes.length > 0) {{
                    var nodeId = params.nodes[0];
                    var node = nodesDataset.get(nodeId);
                    alunoSelecionadoId = nodeId;

                    document.getElementById('edit-nome').innerText = node.label;
                    document.getElementById('edit-info').innerHTML = node.title;

                    var selectTurma = document.getElementById('edit-turma');
                    selectTurma.innerHTML = '';
                    
                    Object.keys(coresTurmas).forEach(function(tNome) {{
                        var opt = document.createElement('option');
                        opt.value = tNome;
                        opt.innerText = tNome;
                        if (tNome === node.group) opt.selected = true;
                        selectTurma.appendChild(opt);
                    }});

                    document.getElementById('sidebar-edit').style.display = 'block';
                }}
            }});

            function confirmarMudancaTurma() {{
                if (!alunoSelecionadoId) return;
                var novaTurma = document.getElementById('edit-turma').value;
                var novaCor = coresTurmas[novaTurma];
                var novaPos = posicoesCentrais[novaTurma];

                nodesDataset.update({{ id: alunoSelecionadoId, group: novaTurma, color: novaCor, x: novaPos.x, y: novaPos.y }});
                rawNodes = rawNodes.map(n => n.id === alunoSelecionadoId ? {{...n, group: novaTurma, color: novaCor, x: novaPos.x, y: novaPos.y}} : n);

                document.getElementById('sidebar-edit').style.display = 'none';
                alunoSelecionadoId = null;
            }}

            function exportarConfiguracaoManual() {{
                var localizacaoMap = {{}};
                var turmasAgrupadas = {{}};
                var mapaObjetos = {{}};
                
                Object.keys(coresTurmas).forEach(function(t) {{ turmasAgrupadas[t] = []; }});

                rawNodes.forEach(function(origNode) {{
                    var nGraf = nodesDataset.get(origNode.id);
                    localizacaoMap[origNode.id] = nGraf.group;
                    mapaObjetos[origNode.id] = origNode;
                    turmasAgrupadas[nGraf.group].push(origNode);
                }});

                var txtOutput = "=========================================================================\\n";
                txtOutput += "   RELATÓRIO DE ALTERAÇÃO MANUAL - ARQUITETURA DE MATRIZ DE TURMAS\\n";
                txtOutput += "=========================================================================\\n\\n";

                txtOutput += "=== 1. COMPOSIÇÃO NOMINAL DAS TURMAS ===\\n\\n";
                Object.keys(turmasAgrupadas).forEach(function(t) {{
                    txtOutput += "--- " + t + " (" + turmasAgrupadas[t].length + " alunos) ---\\n";
                    turmasAgrupadas[t].sort((a,b) => a.label.localeCompare(b.label));
                    
                    turmasAgrupadas[t].forEach(function(a) {{
                        var rtpStr = a.rtp === 1 ? "[RTP]" : "";
                        var mauStr = a.mau === 1 ? "[MAU]" : "";
                        var qeStr = a.qe === 1 ? "[QE]" : "";
                        var qvStr = a.qv === 1 ? "[QV]" : "";
                        var tags = [rtpStr, mauStr, qeStr, qvStr].filter(x => x!=="").join(" ");
                        tags = tags !== "" ? " " + tags : "";
                        
                        txtOutput += "  • " + a.label.padEnd(35) + " | " + a.sexo + " | " + a.lingua.toUpperCase().padEnd(9) + " | Origem: " + a.origem.padEnd(6) + tags + "\\n";
                    }});
                    txtOutput += "\\n";
                }});

                txtOutput += "=== 2. RESUMO ESTATÍSTICO DE TRAÇO DE VARIÁVEIS ===\\n\\n";
                txtOutput += "Turma      | Total | Masc(M) | Fem(F) | Espanhol | Francês | RTP | Mau Comp | Q.Exc | Q.Val \\n";
                txtOutput += "-----------|-------|---------|--------|----------|---------|-----|----------|-------|-------\\n";
                
                Object.keys(turmasAgrupadas).forEach(function(t) {{
                    var list = turmasAgrupadas[t];
                    var m = list.filter(x => x.sexo === 'M').length;
                    var f = list.filter(x => x.sexo === 'F').length;
                    var esp = list.filter(x => x.lingua === 'espanhol').length;
                    var fra = list.filter(x => x.lingua === 'francês').length;
                    var rtp = list.filter(x => x.rtp === 1).length;
                    var mau = list.filter(x => x.mau === 1).length;
                    var qe = list.filter(x => x.qe === 1).length;
                    var qv = list.filter(x => x.qv === 1).length;

                    txtOutput += t.padEnd(10) + " | " + 
                                 list.length.toString().padEnd(5) + " | " + 
                                 m.toString().padEnd(7) + " | " + 
                                 f.toString().padEnd(6) + " | " + 
                                 esp.toString().padEnd(8) + " | " + 
                                 fra.toString().padEnd(7) + " | " + 
                                 rtp.toString().padEnd(3) + " | " + 
                                 mau.toString().padEnd(8) + " | " + 
                                 qe.toString().padEnd(5) + " | " + 
                                 qv.toString().padEnd(5) + "\\n";
                }});
                txtOutput += "\\n";

                txtOutput += "=== 3. AUDITORIA ATUALIZADA DE CUMPRIMENTO DE PEDIDOS ===\\n\\n";
                rawNodes.forEach(function(a) {{
                    var tAtual = localizacaoMap[a.id];
                    
                    if (a.pedidos_pais !== "") {{
                        var parceiros = a.pedidos_pais.split(',').map(x => x.trim().toLowerCase());
                        var validos = parceiros.filter(p => localizacaoMap[p] && localizacaoMap[p] === tAtual);
                        
                        if (validos.length > 0) {{
                            txtOutput += "  ✅ [OK] " + a.label + " (" + tAtual + ") -> Pedido Cumprido (Ficou com: " + validos.map(p => mapaObjetos[p].label).join(", ") + ")\\n";
                        }} else {{
                            txtOutput += "  ❌ [FALHA] " + a.label + " (" + tAtual + ") -> CRITÉRIO VIOLADO! Afastado de todos os amigos pedidos.\\n";
                        }}
                    }}
                }});

                var blob = new Blob([txtOutput], {{type: "text/plain;charset=utf-8"}});
                var aLink = document.createElement("a");
                aLink.href = URL.createObjectURL(blob);
                aLink.download = "auditoria_e_turmas_manuais.txt";
                aLink.click();
            }}
        </script>
    </body>
    </html>"""
    
    with open(ficheiro_saida_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Mapa analítico e interativo gerado com sucesso em '{ficheiro_saida_html}'.")

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    print("A aguardar a seleção do ficheiro Excel...")
    ficheiro_input = filedialog.askopenfilename(
        title="Selecionar Ficheiro da Base de Dados (Excel)",
        filetypes=[("Ficheiros Excel", "*.xlsx *.xls")]
    )
    
    if ficheiro_input:
        try:
            print(f"\nA processar base de dados: {ficheiro_input}\n")
            dados_alunos = carregar_e_ordenar_alunos(ficheiro_input)
            resultado_turmas = distribuir_turmas(dados_alunos, max_por_turma=30, limite_excecao=31, max_por_genero=20)
            
            pasta_origem = os.path.dirname(ficheiro_input)
            ficheiro_saida_excel = os.path.join(pasta_origem, "turmas_finais.xlsx")
            ficheiro_saida_html = os.path.join(pasta_origem, "mapa_turmas.html")
            
            exportar_resultados(resultado_turmas, dados_alunos, ficheiro_saida_excel)
            gerar_mapa_visual(resultado_turmas, dados_alunos, ficheiro_saida_html)
            
            input("\nProcesso concluído com sucesso! Pressiona ENTER para sair...")
        except Exception as e:
            print(f"\nOcorreu um erro técnico: {e}")
            input("Pressiona ENTER para sair...")
    else:
        print("Operação cancelada. Nenhum ficheiro selecionado.")
