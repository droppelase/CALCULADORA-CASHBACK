from flask import Flask, render_template, request, jsonify
import sympy as sp

app = Flask(__name__)

def calcular_logic_dinamico_editavel(data):
    """
    Lógica principal de cálculo com suporte a stakes editáveis dinâmicas
    """
    numero_vias = data.get('numeroVias', 2)
    letras = ['A', 'B', 'C', 'D', 'E'][:numero_vias]
    
    # Extrair dados
    odds = {}
    cashbacks = {}
    
    for letra in letras:
        odds[letra] = data.get(f'odd{letra}', 0)
        cb_percent = data.get(f'cb{letra}', 0)
        cashbacks[letra] = cb_percent / 100 if cb_percent > 1 else cb_percent
    
    # Verificar se há stakes editáveis
    stakes_editaveis = data.get('stakesEditaveis', {})
    stake_fixo_editado = data.get('stakeFixoEditado', None)  # Qual stake foi editado pelo usuário
    
    # Determinar modo de cálculo
    if stake_fixo_editado and stake_fixo_editado in stakes_editaveis:
        # Modo dinâmico: recalcular baseado na stake editada
        stakes = calcular_stakes_dinamico(odds, cashbacks, stakes_editaveis, stake_fixo_editado, numero_vias, letras)
    elif data.get('stakeA', 0) > 0:
        # Modo tradicional: usar stake A como base
        stakes = calcular_stakes_automatico(odds, cashbacks, float(data['stakeA']), numero_vias, letras)
    else:
        return {"status": "erro", "message": "Defina ao menos uma stake ou preencha o campo Stake A.", "lucro": 0, "roi": 0}
    
    # Calcular resultados finais
    total_invested = sum(stakes.values())
    
    # Calcular cashback em valores reais
    cashback_values = {}
    for letra in letras:
        cashback_values[letra] = stakes[letra] * cashbacks[letra]
    
    # Calcular lucro para cada cenário
    scenario_profits = []
    for i in range(numero_vias):
        letra_vencedora = letras[i]
        profit = stakes[letra_vencedora] * odds[letra_vencedora]
        
        # Adicionar cashback das apostas perdedoras
        for j in range(numero_vias):
            letra_perdedora = letras[j]
            if letra_perdedora != letra_vencedora:
                profit += cashback_values[letra_perdedora]
        
        profit -= total_invested
        scenario_profits.append(profit)
    
    # Verificar se é arbitragem perfeita
    is_perfect = all(abs(p - scenario_profits[0]) < 0.01 for p in scenario_profits) and scenario_profits[0] > 0
    
    if is_perfect:
        lucro = scenario_profits[0]
        roi = (lucro / total_invested) * 100
        status = "ok"
        message = None
    else:
        lucro = sum(scenario_profits) / len(scenario_profits)
        roi = (lucro / total_invested) * 100
        status = "perda" if lucro < 0 else "ok"
        if stake_fixo_editado:
            message = f"Stakes recalculadas baseadas na {stake_fixo_editado} editada. Lucro/Perda médio: R$ {lucro:.2f} ({roi:.2f}%)"
        else:
            message = f"Não foi possível garantir lucro em todas as vias. Lucro/Perda médio: R$ {lucro:.2f} ({roi:.2f}%)"
    
    # Preparar resultado
    result = {
        "status": status,
        "lucro": lucro,
        "roi": roi,
        "message": message,
        "total_invested": total_invested,
        "modo_dinamico": stake_fixo_editado is not None
    }
    
    # Adicionar stakes e cashbacks individuais
    for letra in letras:
        result[f'stake{letra}'] = stakes[letra]
        result[f'cb{letra}'] = cashback_values[letra]
    
    return result

def calcular_stakes_dinamico(odds, cashbacks, stakes_editaveis, stake_fixo, numero_vias, letras):
    """
    Calcula stakes dinamicamente baseado em uma stake fixa editada pelo usuário
    """
    stakes = {}
    
    # Definir a stake fixa
    stake_fixo_valor = float(stakes_editaveis[stake_fixo])
    stakes[stake_fixo] = stake_fixo_valor
    
    # Calcular as outras stakes usando sympy para arbitragem perfeita
    stake_symbols = {}
    for letra in letras:
        if letra != stake_fixo:
            stake_symbols[letra] = sp.symbols(f'stake{letra}', real=True, positive=True)
    
    # Criar equações de lucro para cada cenário
    equations = []
    profits = {}
    
    for i in range(numero_vias):
        letra_vencedora = letras[i]
        profit = 0
        
        # Lucro da aposta vencedora
        if letra_vencedora == stake_fixo:
            profit += stakes[stake_fixo] * odds[letra_vencedora]
        else:
            profit += stake_symbols[letra_vencedora] * odds[letra_vencedora]
        
        # Cashback das apostas perdedoras
        for j in range(numero_vias):
            letra_perdedora = letras[j]
            if letra_perdedora != letra_vencedora:
                if letra_perdedora == stake_fixo:
                    profit += stakes[stake_fixo] * cashbacks[letra_perdedora]
                else:
                    profit += stake_symbols[letra_perdedora] * cashbacks[letra_perdedora]
        
        # Subtrair total investido
        total_invested = stakes[stake_fixo]
        for letra in letras:
            if letra != stake_fixo:
                total_invested += stake_symbols[letra]
        
        profit -= total_invested
        profits[letra_vencedora] = profit
    
    # Criar equações para arbitragem perfeita (todos os lucros iguais)
    base_profit = profits[letras[0]]
    for i in range(1, numero_vias):
        letra = letras[i]
        equations.append(sp.Eq(base_profit, profits[letra]))
    
    # Resolver o sistema de equações
    symbols_to_solve = [stake_symbols[letra] for letra in letras if letra != stake_fixo]
    
    try:
        if len(symbols_to_solve) > 0:
            solutions = sp.solve(equations, symbols_to_solve, dict=True)
            
            if solutions and len(solutions) > 0:
                sol = solutions[0]
                
                # Verificar se todas as soluções são positivas
                all_positive = True
                for letra in letras:
                    if letra != stake_fixo:
                        symbol_key = stake_symbols[letra]
                        if symbol_key in sol and sol[symbol_key] > 0:
                            stakes[letra] = float(sol[symbol_key])
                        else:
                            all_positive = False
                            break
                
                if not all_positive:
                    # Fallback para distribuição proporcional
                    stakes = calcular_stakes_proporcionais_com_fixo(odds, stake_fixo, stake_fixo_valor, numero_vias, letras)
            else:
                # Fallback para distribuição proporcional
                stakes = calcular_stakes_proporcionais_com_fixo(odds, stake_fixo, stake_fixo_valor, numero_vias, letras)
        else:
            # Caso especial: apenas uma via (não deveria acontecer)
            stakes = {stake_fixo: stake_fixo_valor}
            
    except Exception:
        # Fallback para distribuição proporcional
        stakes = calcular_stakes_proporcionais_com_fixo(odds, stake_fixo, stake_fixo_valor, numero_vias, letras)
    
    return stakes

def calcular_stakes_proporcionais_com_fixo(odds, stake_fixo, stake_fixo_valor, numero_vias, letras):
    """
    Calcula stakes proporcionais baseado em uma stake fixa
    """
    # Calcular probabilidades implícitas
    implied_probs = {}
    total_implied = 0
    
    for letra in letras:
        implied_probs[letra] = 1 / odds[letra]
        total_implied += implied_probs[letra]
    
    # Normalizar probabilidades
    for letra in implied_probs:
        implied_probs[letra] /= total_implied
    
    # Calcular orçamento total baseado na stake fixa
    total_budget = stake_fixo_valor / implied_probs[stake_fixo]
    
    # Calcular stakes proporcionais
    stakes = {}
    for letra in letras:
        if letra == stake_fixo:
            stakes[letra] = stake_fixo_valor
        else:
            stakes[letra] = total_budget * implied_probs[letra]
    
    return stakes

def calcular_stakes_automatico(odds, cashbacks, stake_a, numero_vias, letras):
    """
    Calcula stakes automaticamente usando sympy para arbitragem perfeita
    """
    stakes = {'A': stake_a}
    
    # Calcular stakes para as outras vias usando sympy
    stake_symbols = {}
    for i in range(1, numero_vias):
        letra = letras[i]
        stake_symbols[letra] = sp.symbols(f'stake{letra}', real=True, positive=True)
    
    # Criar equações de lucro para cada cenário
    equations = []
    profits = {}
    
    for i in range(numero_vias):
        letra_vencedora = letras[i]
        profit = 0
        
        # Lucro da aposta vencedora
        if letra_vencedora == 'A':
            profit += stakes['A'] * odds['A']
        else:
            profit += stake_symbols[letra_vencedora] * odds[letra_vencedora]
        
        # Cashback das apostas perdedoras
        for j in range(numero_vias):
            letra_perdedora = letras[j]
            if letra_perdedora != letra_vencedora:
                if letra_perdedora == 'A':
                    profit += stakes['A'] * cashbacks[letra_perdedora]
                else:
                    profit += stake_symbols[letra_perdedora] * cashbacks[letra_perdedora]
        
        # Subtrair total investido
        total_invested = stakes['A']
        for k in range(1, numero_vias):
            total_invested += stake_symbols[letras[k]]
        
        profit -= total_invested
        profits[letra_vencedora] = profit
    
    # Criar equações para arbitragem perfeita (todos os lucros iguais)
    base_profit = profits['A']
    for i in range(1, numero_vias):
        letra = letras[i]
        equations.append(sp.Eq(base_profit, profits[letra]))
    
    # Resolver o sistema de equações
    symbols_to_solve = [stake_symbols[letras[i]] for i in range(1, numero_vias)]
    
    try:
        solutions = sp.solve(equations, symbols_to_solve, dict=True)
        
        if solutions and len(solutions) > 0:
            sol = solutions[0]
            
            # Verificar se todas as soluções são positivas
            all_positive = True
            for i in range(1, numero_vias):
                letra = letras[i]
                symbol_key = stake_symbols[letra]
                if symbol_key in sol and sol[symbol_key] > 0:
                    stakes[letra] = float(sol[symbol_key])
                else:
                    all_positive = False
                    break
            
            if not all_positive:
                # Fallback para distribuição proporcional
                stakes = calcular_stakes_proporcionais(odds, stakes['A'], numero_vias, letras)
        else:
            # Fallback para distribuição proporcional
            stakes = calcular_stakes_proporcionais(odds, stakes['A'], numero_vias, letras)
            
    except Exception:
        # Fallback para distribuição proporcional
        stakes = calcular_stakes_proporcionais(odds, stakes['A'], numero_vias, letras)
    
    return stakes

def calcular_stakes_proporcionais(odds, stake_a, numero_vias, letras):
    """
    Calcula stakes proporcionais baseado nas probabilidades implícitas
    """
    # Calcular probabilidades implícitas
    implied_probs = {}
    total_implied = 0
    
    for i in range(numero_vias):
        letra = letras[i]
        implied_probs[letra] = 1 / odds[letra]
        total_implied += implied_probs[letra]
    
    # Normalizar probabilidades
    for letra in implied_probs:
        implied_probs[letra] /= total_implied
    
    # Calcular orçamento total baseado no stake A
    total_budget = stake_a / implied_probs['A']
    
    # Calcular stakes proporcionais
    stakes = {}
    for i in range(numero_vias):
        letra = letras[i]
        if letra == 'A':
            stakes[letra] = stake_a
        else:
            stakes[letra] = total_budget * implied_probs[letra]
    
    return stakes

@app.route("/")
def index():
    return render_template("index_dinamico.html")

@app.route("/calcular", methods=["POST"])
def calcular():
    data = request.get_json()
    
    try:
        result = calcular_logic_dinamico_editavel(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "erro",
            "message": f"Erro no cálculo: {str(e)}",
            "lucro": 0,
            "roi": 0
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

