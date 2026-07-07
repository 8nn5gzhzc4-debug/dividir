import math
import openpyxl
import os
import tkinter as tk
from tkinter import filedialog

def carregar_e_ordenar_alunos(caminho_excel):
    # Lê o Excel usando apenas openpyxl (muito mais leve e rápido)
    wb = openpyxl.load_workbook(caminho_excel, data_only=True)
    sheet = wb.active
    
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
        
    headers = [str(c).strip() if c else "" for c in rows[0]]
    lista_alunos = []
    
    for row in rows[1:]:
        if all(v is None for v in row): continue # Ignora linhas vazias
        
        aluno = dict(zip(headers, row))
        
        # Funções de limpeza sem usar o Pandas
        def safe_int(val):
            try: return int(float(val)) if val is not None else 0
            except: return 0
            
        def safe_str(val, default=""):
            if val is None: return default
            v_str = str(val).strip()
            if v_str in ["", "nan", "None"]: return default
            return v_str

        aluno['RTP'] = safe_int(aluno.get('RTP'))
        aluno['Mau_Comportamento'] = safe_int(aluno.get('Mau_Comportamento'))
        aluno['QE'] = safe_int(aluno.get('QE'))
        aluno['Agrupar_Com_Pais'] = safe_str(aluno.get('Agrupar_Com_Pais'))
        aluno['Separar_De_Pais'] = safe_str(aluno.get('Separar_De_Pais'))
        aluno['Agrupar_Com_Professores'] = safe_str(aluno.get('Agrupar_Com_Professores'))
        aluno['Separar_De_Professores'] = safe_str(aluno.get('Separar_De_Professores'))
        aluno['Turma_Origem'] = safe_str(aluno.get('Turma_Origem'), "Desconhecida")
        aluno['Artes'] = safe_str(aluno.get('Artes'), "Música")
        aluno['Lingua'] = safe_str(aluno.get('Lingua'), "")
        aluno['Sexo'] = safe_str(aluno.get('Sexo'), "")
        aluno['Nome'] = safe_str(aluno.get('Nome'), "")
        
        lista_alunos.append(aluno)
        
    # Ordenação por prioridade inicial
    lista_alunos.sort(key=lambda x: (-x['RTP'], -x['Mau_Comportamento'], -x['QE'], x['Sexo']))
    return lista_alunos

def distribuir_turmas(lista_alunos, max_por_turma=30):
    nomes_turmas = ["7.º A", "7.º B", "7.º C", "7.º D", "7.º E", "7.º F", "7.º G", "7.º H"]
    num_total_turmas = len(nomes_turmas)
    turmas = {nome: [] for nome in nomes_turmas}
    
    total_alunos = len(lista_alunos)
    media_ideal_alunos = total_alunos / num_total_turmas
    total_espanhol = sum(1 for a in lista_alunos if a['Lingua'].lower() == 'espanhol')
    
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
                turma_
