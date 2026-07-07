import math
import pandas as pd

def carregar_e_ordenar_alunos(caminho_excel):
    df = pd.read_excel(caminho_excel)
    
    df['RTP'] = df['RTP'].fillna(0).astype(int)
    df['Mau_Comportamento'] = df['Mau_Comportamento'].fillna(0).astype(int)
    df['QE'] = df['QE'].fillna(0).astype(int)
    df['Agrupar_Com_Pais'] = df['Agrupar_Com_Pais'].fillna("").astype(str)
    df['Separar_De_Pais'] = df['Separar_De_Pais'].fillna("").astype(str)
    df['Agrupar_Com_Professores'] = df['Agrupar_Com_Professores'].fillna("").astype(str)
    df['Separar_De_Professores'] = df['Separar_De_Professores'].fillna("").astype(str)
    df['Turma_Origem'] = df['Turma_Origem'].fillna("Desconhecida").astype(str)
    
    if 'Artes' not in df.columns:
        df['Artes'] = "Música"
    df['Artes'] = df['Artes'].fillna("Música").astype(str)
    
    df = df.sort_values(by=['RTP', 'Mau_Comportamento', 'QE', 'Sexo'], ascending=[False, False, False, True]).reset_index(drop=True)
    return df

def distribuir_turmas(df, max_por_turma=30):
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

    def obter_turmas_elegiveis_individual(lingua_aluno):
        elegiveis = []
        for t in nomes_turmas:
            contagem = turmas[t]
            if len(contagem) + 1 > max_por_turma: continue
                
            esp_na_turma = sum(1 for x in contagem if x['Lingua'].lower() == 'espanhol')
            fra_na_turma = sum(1 for x in contagem if x['Lingua'].lower() == 'francês')
            
            if lingua_aluno == 'espanhol':
                if t in turmas_exclusivas_frances: continue
                if t == turma_mista and esp_na_turma + 1 > vagas_espanhol_na_mista: continue
                elegiveis.append(t)
            else:
                if t in turmas_espanhol and t != turma_mista: continue
                if t == turma_mista and fra_na_turma + 1 > (media_ideal_alunos - vagas_espanhol_na_mista): continue
                elegiveis.append(t)
        return elegiveis if elegiveis else (turmas_espanhol if lingua_aluno == 'espanhol' else turmas_exclusivas_frances)

    def taxa(t, lingua, feature):
        count = sum(1 for x in turmas[t] if x[feature] == 1 and x['Lingua'].lower() == lingua)
        if lingua == 'espanhol':
            cap = vagas_espanhol_na_mista if t == turma_mista else media_ideal_alunos
        else:
            cap = (media_ideal_alunos - vagas_espanhol_na_mista) if t == turma_mista else media_ideal_alunos
        return count / cap if cap > 0 else 0

    def alocar_grupo(grupo_total, misto):
        if misto:
            if turma_mista:
                contagem = turmas[turma_mista]
                esp_na_mista = sum(1 for x in contagem if x['Lingua'].lower() == 'espanhol')
                fra_na_mista = sum(1 for x in contagem if x['Lingua'].lower() == 'francês')
                num_esp_g = sum(1 for x in grupo_total if x['Lingua'].lower() == 'espanhol')
                num_fra_g = sum(1 for x in grupo_total if x['Lingua'].lower() == 'francês')
                
                if (len(contagem) + len(grupo_total) <= max_por_turma and
                    esp_na_mista + num_esp_g <= vagas_espanhol_na_mista and
                    fra_na_mista + num_fra_g <= (media_ideal_alunos - vagas_espanhol_na_mista)):
                    
                    if all(pode_ficar_na_turma_imperativo(m, turmas[turma_mista]) for m in grupo_total):
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
                if len(contagem) + len(grupo_total) > max_por_turma: continue
                
                esp_na_turma = sum(1 for x in contagem if x['Lingua'].lower() == 'espanhol')
                fra_na_turma = sum(1 for x in contagem if x['Lingua'].lower() == 'francês')
                
                if lingua_comum == 'espanhol':
                    if t in turmas_espanhol:
                        if t == turma_mista and esp_na_turma + len(grupo_total) > vagas_espanhol_na_mista: continue
                        turmas_elegiveis.append(t)
                else:
                    if t in turmas_espanhol and t != turma_mista: continue
                    if t == turma_mista and fra_na_turma + len(grupo_total) > (media_ideal_alunos - vagas_espanhol_na_mista): continue
                    turmas_elegiveis.append(t)

            if not turmas_elegiveis: return False
            
            turmas_validas = [t for t in turmas_elegiveis if all(pode_ficar_na_turma_imperativo(m, turmas[t]) for m in grupo_total)]
            if not turmas_validas:
                turmas_validas = turmas_elegiveis
            
            def avaliar_turma_grupo(t):
                score_rtp = sum(1 for x in turmas[t] if x['RTP'] == 1) if any(g['RTP'] == 1 for g in grupo_total) else 0
                score_mau = sum(1 for x in turmas[t] if x['Mau_Comportamento'] == 1) if any(g['Mau_Comportamento'] == 1 for g in grupo_total) else 0
                score_qe = sum(1 for x in turmas[t] if x['QE'] == 1) if any(g['QE'] == 1 for g in grupo_total) else 0
                
                score_prof = sum(avaliar_sugestoes_professores(g, turmas[t]) for g in grupo_total)
                origem_count = sum(1 for x in turmas[t] for g in grupo_total if x['Turma_Origem'] == g['Turma_Origem'])
                score_artes = sum(1 for x in turmas[t] if x['Artes'].lower() == grupo_total[0]['Artes'].lower())
                
                return (score_rtp, score_mau, score_qe, origem_count, score_prof, score_artes, len(turmas[t]))

            turma_destino = min(turmas_validas, key=avaliar_turma_grupo)
            for membro in grupo_total:
                turmas[turma_destino].append(membro)
                alunos_processados.add(membro['Nome'])
            return True

    def alocar_individual(aluno):
        lingua_aluno = aluno['Lingua'].lower()
        arte_aluno = aluno['Artes'].lower()
        turmas_elegiveis = obter_turmas_elegiveis_individual(lingua_aluno)

        def key_individual(t):
            return (
                taxa(t, lingua_aluno, 'RTP') if aluno['RTP'] == 1 else 0,
                taxa(t, lingua_aluno, 'Mau_Comportamento') if aluno['Mau_Comportamento'] == 1 else 0,
                taxa(t, lingua_aluno, 'QE') if aluno['QE'] == 1 else 0,
                sum(1 for x in turmas[t] if x['Turma_Origem'] == aluno['Turma_Origem']),
                avaliar_sugestoes_professores(aluno, turmas[t]),
                sum(1 for x in turmas[t] if x['Artes'].lower() == arte_aluno),
                sum(1 for x in turmas[t] if x['Sexo'] == aluno['Sexo']),
                len(turmas[t])
            )

        turma_destino = min(turmas_elegiveis, key=key_individual)
        if not pode_ficar_na_turma_imperativo(aluno, turmas[turma_destino]):
            alternativas = [t for t in turmas_elegiveis if t != turma_destino and pode_ficar_na_turma_imperativo(aluno, turmas[t])]
            if alternativas:
                turma_destino = min(alternativas, key=key_individual)

        turmas[turma_destino].append(aluno)
        alunos_processados.add(aluno['Nome'])

    parent = {a['Nome'].lower(): a['Nome'].lower() for a in lista_alunos}

    def find(x):
        raiz = x
        while parent[raiz] != raiz:
            raiz = parent[raiz]
        while parent[x] != raiz:
            parent[x], x = raiz, parent[x]
        return raiz

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for aluno in lista_alunos:
        nome_l = aluno['Nome'].lower()
        parceiros = [n.strip().lower() for n in aluno['Agrupar_Com_Pais'].split(',') if n.strip()]
        for p in parceiros:
            if p in parent:
                union(nome_l, p)

    grupos_por_raiz = {}
    for aluno in lista_alunos:
        raiz = find(aluno['Nome'].lower())
        grupos_por_raiz.setdefault(raiz, []).append(aluno)

    grupos_de_pedidos = [g for g in grupos_por_raiz.values() if len(g) > 1]
    grupos_de_pedidos_limpos = []
    
    for grupo in grupos_de_pedidos:
        nomes_grupo = {m['Nome'].lower() for m in grupo}
        conflito_interno = False
        for m in grupo:
            vetos_pais = {v.strip().lower() for v in m['Separar_De_Pais'].split(',') if v.strip()}
            if vetos_pais & nomes_grupo:
                conflito_interno = True
                print(f"⚠️ CONFLITO IMPERATIVO: Pedido de juntar e separar os mesmos alunos ({m['Nome']}). O grupo foi dissolvido.")
                break
        if not conflito_interno:
            grupos_de_pedidos_limpos.append(grupo)

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

    print("\nA iniciar motor iterativo de trocas...")
    
    def obter_mapeamento_atual():
        return {alu['Nome'].lower(): t_nome for t_nome, lista in turmas.items() for alu in lista}

    def quebra_grupo_existente(aluno_teste, turma_lista):
        nome_teste = aluno_teste['Nome'].lower()
        pedidos_do_aluno = [n.strip().lower() for n in aluno_teste['Agrupar_Com_Pais'].split(',') if n.strip()]
        if any(p in [x['Nome'].lower() for x in turma_lista] for p in pedidos_do_aluno): return True
        for x in turma_lista:
            pedidos_de_x = [n.strip().lower() for n in x['Agrupar_Com_Pais'].split(',') if n.strip()]
            if nome_teste in pedidos_de_x: return True
        return False

    for iteracao in range(15):
        aluno_turma = obter_mapeamento_atual()
        troca_feita_nesta_iteracao = False
        
        for aluno in lista_alunos:
            nome_aluno_l = aluno['Nome'].lower()
            if aluno['Agrupar_Com_Pais'] == "" or nome_aluno_l not in aluno_turma: continue
                
            parceiros = [n.strip() for n in aluno['Agrupar_Com_Pais'].split(',') if n.strip()]
            for par_nome in parceiros:
                par_l = par_nome.lower()
                if par_l not in aluno_turma: continue
                
                turma_atual = aluno_turma[nome_aluno_l]
                turma_alvo = aluno_turma[par_l]
                if turma_atual == turma_alvo: continue
                if quebra_grupo_existente(aluno, turmas[turma_atual]): continue
                
                lingua_aluno = aluno['Lingua'].lower()
                candidato_troca = None
                
                for potencial in turmas[turma_alvo]:
                    if (potencial['RTP'] == 0 and 
                        potencial['Mau_Comportamento'] == 0 and 
                        potencial['Agrupar_Com_Pais'] == "" and
                        potencial['Lingua'].lower() == lingua_aluno):
                        
                        if quebra_grupo_existente(potencial, turmas[turma_alvo]): continue
                        
                        temp_alvo = [x for x in turmas[turma_alvo] if x['Nome'] != potencial['Nome']]
                        temp_atual = [x for x in turmas[turma_atual] if x['Nome'] != aluno['Nome']]
                        
                        if (pode_ficar_na_turma_imperativo(aluno, temp_alvo) and pode_ficar_na_turma_imperativo(potencial, temp_atual) and
                            avaliar_sugestoes_professores(aluno, temp_alvo) <= 0 and avaliar_sugestoes_professores(potencial, temp_atual) <= 0):
                            candidato_troca = potencial
                            break
                
                if not candidato_troca:
                    for potencial in turmas[turma_alvo]:
                        if (potencial['RTP'] <= aluno['RTP'] and 
                            potencial['Mau_Comportamento'] <= aluno['Mau_Comportamento'] and
                            potencial['Agrupar_Com_Pais'] == "" and
                            potencial['Lingua'].lower() == lingua_aluno):
                            
                            if quebra_grupo_existente(potencial, turmas[turma_alvo]): continue
                                
                            temp_alvo = [x for x in turmas[turma_alvo] if x['Nome'] != potencial['Nome']]
                            temp_atual = [x for x in turmas[turma_atual] if x['Nome'] != aluno['Nome']]
                            
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

    print("\nA nivelar as estatísticas finais...")
    def balancear_caracteristica(feature):
        for _ in range(20):
            contagens = {t: sum(1 for a in turmas[t] if a[feature] == 1) for t in nomes_turmas}
            max_t = max(contagens, key=contagens.get)
            min_t = min(contagens, key=contagens.get)

            if contagens[max_t] - contagens[min_t] <= 1: break 

            troca_feita = False
            for mau_aluno in turmas[max_t]:
                if mau_aluno[feature] == 1 and not quebra_grupo_existente(mau_aluno, turmas[max_t]):
                    for bom_aluno in turmas[min_t]:
                        if (bom_aluno[feature] == 0 and 
                            not quebra_grupo_existente(bom_aluno, turmas[min_t]) and 
                            bom_aluno['Lingua'].lower() == mau_aluno['Lingua'].lower()):
                            
                            temp_max = [x for x in turmas[max_t] if x['Nome'] != mau_aluno['Nome']]
                            temp_min = [x for x in turmas[min_t] if x['Nome'] != bom_aluno['Nome']]

                            if pode_ficar_na_turma_imperativo(mau_aluno, temp_min) and pode_ficar_na_turma_imperativo(bom_aluno, temp_max):
                                turmas[max_t].remove(mau_aluno)
                                turmas[min_t].remove(bom_aluno)
                                turmas[min_t].append(mau_aluno)
                                turmas[max_t].append(bom_aluno)
                                troca_feita = True
                                break
                    if troca_feita: break
            if not troca_feita: break

    balancear_caracteristica('RTP')
    balancear_caracteristica('Mau_Comportamento')

    return turmas

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
            df_salvar = df_turma.drop(columns=['Prioridade'], errors='ignore')
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
                "QE": df_turma['QE'].sum()
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
        
        # Validar Agrupar (Pais)
        if str(aluno.get('Agrupar_Com_Pais', '')) not in ["", "nan", "None"]:
            parceiros = [n.strip() for n in str(aluno['Agrupar_Com_Pais']).split(',') if n.strip()]
            for p in parceiros:
                p_lower = p.lower()
                if p_lower in aluno_turma:
                    turma_alvo = aluno_turma[p_lower]
                    alvo_completo = aluno_dit[p_lower]
                    status = "✅ Cumprido" if turma_atual == turma_alvo else "❌ Falhou Crítico"
                    motivo = "-"
                    if status.startswith("❌"):
                        vetos_aluno = [v.strip().lower() for v in str(aluno.get('Separar_De_Pais', '')).split(',') if v.strip()]
                        vetos_alvo = [v.strip().lower() for v in str(alvo_completo.get('Separar_De_Pais', '')).split(',') if v.strip()]
                        if p_lower in vetos_aluno or nome_aluno_lower in vetos_alvo:
                            motivo = "Paradoxo: Pedido para juntar e separar os mesmos alunos em simultâneo."
                        elif aluno['Lingua'].lower() != alvo_completo['Lingua'].lower():
                            motivo = "Conflito de Língua (lotação máxima na turma mista)."
                        else:
                            motivo = "Limite de turma (30) excedido ou conflito direto com vetos de pais de outros alunos."

                    validacoes.append({"Aluno": nome_aluno, "Tipo Pedido": "Agrupar (Pais)", "Alvo": p, "Turma Aluno": turma_atual, "Turma Alvo": turma_alvo, "Estado": status, "Motivo Falha": motivo})
                else:
                    validacoes.append({"Aluno": nome_aluno, "Tipo Pedido": "Agrupar (Pais)", "Alvo": p, "Turma Aluno": turma_atual, "Turma Alvo": "-", "Estado": "⚠️ Alvo Inválido", "Motivo Falha": "Aluno alvo não consta na base de dados."})
        
        # Validar Separar (Pais)
        if str(aluno.get('Separar_De_Pais', '')) not in ["", "nan", "None"]:
            vetos = [n.strip() for n in str(aluno['Separar_De_Pais']).split(',') if n.strip()]
            for v in vetos:
                v_lower = v.lower()
                if v_lower in aluno_turma:
                    turma_alvo = aluno_turma[v_lower]
                    status = "✅ Cumprido" if turma_atual != turma_alvo else "❌ Falhou Crítico"
                    motivo = "-" if status.startswith("✅") else "Erro crítico de processamento."
                    validacoes.append({"Aluno": nome_aluno, "Tipo Pedido": "Separar (Pais)", "Alvo": v, "Turma Aluno": turma_atual, "Turma Alvo": turma_alvo, "Estado": status, "Motivo Falha": motivo})

        # Validar Agrupar (Profs)
        if str(aluno.get('Agrupar_Com_Professores', '')) not in ["", "nan", "None"]:
            pedidos_prof = [n.strip() for n in str(aluno['Agrupar_Com_Professores']).split(',') if n.strip()]
            for p in pedidos_prof:
                p_lower = p.lower()
                if p_lower in aluno_turma:
                    turma_alvo = aluno_turma[p_lower]
                    status = "✅ Cumprido" if turma_atual == turma_alvo else "⚠️ Ignorado (Sugestão)"
                    motivo = "-" if status.startswith("✅") else "Sugestão preterida para manter equilíbrio rigoroso ou respeitar regras imperativas."
                    validacoes.append({"Aluno": nome_aluno, "Tipo Pedido": "Agrupar (Prof)", "Alvo": p, "Turma Aluno": turma_atual, "Turma Alvo": turma_alvo, "Estado": status, "Motivo Falha": motivo})

        # Validar Separar (Profs)
        if str(aluno.get('Separar_De_Professores', '')) not in ["", "nan", "None"]:
            vetos_prof = [n.strip() for n in str(aluno['Separar_De_Professores']).split(',') if n.strip()]
            for v in vetos_prof:
                v_lower = v.lower()
                if v_lower in aluno_turma:
                    turma_alvo = aluno_turma[v_lower]
                    status = "✅ Cumprido" if turma_atual != turma_alvo else "⚠️ Ignorado (Sugestão)"
                    motivo = "-" if status.startswith("✅") else "Sugestão preterida para manter equilíbrio rigoroso ou respeitar regras imperativas."
                    validacoes.append({"Aluno": nome_aluno, "Tipo Pedido": "Separar (Prof)", "Alvo": v, "Turma Aluno": turma_atual, "Turma Alvo": turma_alvo, "Estado": status, "Motivo Falha": motivo})

    if validacoes:
        pd.DataFrame(validacoes).to_excel(writer, sheet_name="Validação de Pedidos", index=False)
    else:
        pd.DataFrame([{"Aviso": "Nenhum pedido de agrupamento ou separação registado."}]).to_excel(writer, sheet_name="Validação de Pedidos", index=False)

    writer.close()
    print(f"\nResultados guardados com sucesso no ficheiro '{ficheiro_saida}'.")

if __name__ == "__main__":
    ficheiro_input = "alunos.xlsx" 
    try:
        dados_alunos = carregar_e_ordenar_alunos(ficheiro_input)
        resultado_turmas = distribuir_turmas(dados_alunos, max_por_turma=30)
        exportar_resultados(resultado_turmas, dados_alunos)
    except FileNotFoundError:
        print(f"Erro: O ficheiro '{ficheiro_input}' não foi encontrado.")

if __name__ == "__main__":
    import tkinter as tk
    from tkinter import filedialog
    import os

    # Iniciar e ocultar a janela principal do Tkinter
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
            resultado_turmas = distribuir_turmas(dados_alunos, max_por_turma=30)
            
            # O ficheiro final será gerado automaticamente na mesma pasta do ficheiro original
            pasta_origem = os.path.dirname(ficheiro_input)
            ficheiro_saida = os.path.join(pasta_origem, "turmas_finais.xlsx")
            
            exportar_resultados(resultado_turmas, dados_alunos, ficheiro_saida)
            input("\nProcesso concluído com sucesso! Pressiona ENTER para sair...")
        except Exception as e:
            print(f"\nOcorreu um erro técnico: {e}")
            input("Pressiona ENTER para sair...")
    else:
        print("Operação cancelada. Nenhum ficheiro selecionado.")
