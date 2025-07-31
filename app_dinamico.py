from flask import Flask, render_template, request, jsonify
import sympy as sp

app = Flask(__name__)

def calcular_logic_dinamico_editavel(data):
    """
    Lógica principal de cálculo com suporte a stakes editáveis
    """
    numero_vias = data.get('numeroVias', 2)
    letras = ['A', 'B', 'C', 'D', 'E'][:numero_vias]
    
    # Extrair dados
    odds = {}
    cashbacks = {}
    stakes = {}
    
    for letra in letras:
        odds[letra] = data.get(f'odd{letra}', 0)
        cb_percent = data.get(f'cb{letra}', 0)
        cashbacks[letra] = cb_percent / 100 if cb_percent > 1 else cb_percent
    
    # Stake A sempre vem do campo principal
    stakes['A'] = float(data['stakeA'])
    if stakes['A'] <= 0:
        return {"status": "erro", "message": "Stake A deve ser maior que 0.", "lucro": 0, "roi": 0}
    
    # Verificar se estamos em modo de edição
    modo_edicao = data.get('modoEdicao', False)
    stakes_editaveis = data.get('stakesEditaveis', {})
    
    if modo_edicao and stakes_editaveis:
        # Modo híbrido: usar stakes editáveis e calcular os restantes proporcionalmente
        stakes = calcular_stakes_hibrido(odds, cashbacks, stakes['A'], numero_vias, letras, stakes_editaveis)
    else:
        # Modo automático: calcular todos os stakes via arbitragem
        stakes = calcular_stakes_automatico(odds, cashbacks, stakes['A'], numero_vias, letras)
    
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
        if modo_edicao:
            message = f"Stakes editados manualmente. Lucro/Perda médio: R$ {lucro:.2f} ({roi:.2f}%)"
        else:
            message = f"Não foi possível garantir lucro em todas as vias. Lucro/Perda médio: R$ {lucro:.2f} ({roi:.2f}%)"
    
    # Preparar resultado
    result = {
        "status": status,
        "lucro": lucro,
        "roi": roi,
        "message": message,
        "total_invested": total_invested
    }
    
    # Adicionar stakes e cashbacks individuais
    for letra in letras:
        result[f'stake{letra}'] = stakes[letra]
        result[f'cb{letra}'] = cashback_values[letra]
    
    return result

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

def calcular_stakes_hibrido(odds, cashbacks, stake_a, numero_vias, letras, stakes_editaveis):
    """
    Calcula stakes em modo híbrido: alguns editados manualmente, outros ajustados proporcionalmente
    """
    stakes = {'A': stake_a}
    
    # Adicionar stakes editáveis
    for letra, valor in stakes_editaveis.items():
        if letra != 'A':  # A não pode ser editado aqui
            stakes[letra] = float(valor)
    
    # Para vias não editadas, calcular proporcionalmente baseado nas editadas
    vias_nao_editadas = []
    for i in range(1, numero_vias):
        letra = letras[i]
        if letra not in stakes_editaveis:
            vias_nao_editadas.append(letra)
    
    if vias_nao_editadas:
        # Calcular stakes proporcionais para as vias não editadas
        # Usar a mesma lógica de probabilidades implícitas
        total_budget_usado = sum(stakes.values())
        
        # Calcular probabilidades implícitas das vias não editadas
        implied_probs = {}
        total_implied = 0
        
        for letra in vias_nao_editadas:
            implied_probs[letra] = 1 / odds[letra]
            total_implied += implied_probs[letra]
        
        if total_implied > 0:
            # Normalizar probabilidades
            for letra in implied_probs:
                implied_probs[letra] /= total_implied
            
            # Estimar orçamento restante (baseado na proporção das vias editadas)
            budget_restante = total_budget_usado * 0.3  # Estimativa conservadora
            
            # Distribuir orçamento restante proporcionalmente
            for letra in vias_nao_editadas:
                stakes[letra] = budget_restante * implied_probs[letra]
    
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