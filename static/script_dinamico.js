// Variáveis globais
let numeroVias = 2;
const letras = ['A', 'B', 'C', 'D', 'E'];
let stakesEditaveis = {};
let stakeFixoEditado = null; // Qual stake foi editada pelo usuário
let ultimosValoresStakes = {}; // Para detectar mudanças

// Inicializar a página
document.addEventListener('DOMContentLoaded', function() {
    gerarCampos();
    atualizarContador();
    atualizarBotoes();
});

function gerarCampos() {
    const container = document.getElementById('campos-container');
    container.innerHTML = '';
    
    // Criar uma única linha para todas as vias
    const row = document.createElement('div');
    row.className = 'row g-2'; // Reduzir gap entre colunas
    
    for (let i = 0; i < numeroVias; i++) {
        const letra = letras[i];
        const col = document.createElement('div');
        
        // Layout responsivo melhorado para 5 vias
        if (numeroVias === 5) {
            // Para 5 vias: usar largura fixa com cálculo preciso
            col.className = 'col mb-3';
            col.style.flex = '0 0 19.2%'; // 19.2% x 5 = 96% (deixa 4% para gaps)
            col.style.maxWidth = '19.2%';
        } else if (numeroVias === 4) {
            col.className = 'col-lg-3 col-md-6 col-sm-6 mb-3';
        } else if (numeroVias === 3) {
            col.className = 'col-lg-4 col-md-4 col-sm-6 mb-3';
        } else {
            col.className = 'col-lg-6 col-md-6 col-sm-6 mb-3';
        }
        
        col.innerHTML = `
            <div class="card bg-dark text-white h-100">
                <div class="card-header bg-success text-center">
                    <h6 class="mb-0">📊 Via ${letra}</h6>
                </div>
                <div class="card-body p-2">
                    <div class="input-group mb-2">
                        <span class="input-group-text">Odd</span>
                        <input type="number" class="form-control" id="odd${letra}" step="0.01" oninput="calcular()" placeholder="2.50">
                    </div>
                    <div class="input-group mb-2">
                        <span class="input-group-text">Cashback (%)</span>
                        <input type="number" class="form-control" id="cb${letra}" step="0.01" oninput="calcular()" placeholder="10">
                    </div>
                    <div class="input-group mb-2">
                        <span class="input-group-text">Stake (R$)</span>
                        <input type="number" class="form-control stake-input" id="stake${letra}" step="0.01" oninput="editarStake('${letra}', this.value)" placeholder="1000">
                    </div>
                    <div class="cashback-display">
                        <small class="text-muted">Cashback (R$): <span id="cbValue${letra}">0.00</span></small>
                    </div>
                </div>
            </div>
        `;
        
        row.appendChild(col);
    }
    
    container.appendChild(row);
}

function adicionarVia() {
    if (numeroVias < 5) {
        numeroVias++;
        gerarCampos();
        atualizarContador();
        atualizarBotoes();
        calcular();
    }
}

function removerVia() {
    if (numeroVias > 2) {
        numeroVias--;
        gerarCampos();
        atualizarContador();
        atualizarBotoes();
        calcular();
    }
}

function atualizarContador() {
    document.getElementById('contador-vias').textContent = `${numeroVias} vias ativas`;
}

function atualizarBotoes() {
    const btnAdicionar = document.getElementById('btn-adicionar');
    const btnRemover = document.getElementById('btn-remover');
    
    if (numeroVias >= 5) {
        btnAdicionar.textContent = '➕ Máximo atingido';
        btnAdicionar.disabled = true;
        btnAdicionar.className = 'btn btn-secondary me-2';
    } else {
        btnAdicionar.textContent = '➕ Adicionar Via';
        btnAdicionar.disabled = false;
        btnAdicionar.className = 'btn btn-success me-2';
    }
    
    if (numeroVias <= 2) {
        btnRemover.textContent = '➖ Mínimo atingido';
        btnRemover.disabled = true;
        btnRemover.className = 'btn btn-secondary me-2';
    } else {
        btnRemover.textContent = '➖ Remover Via';
        btnRemover.disabled = false;
        btnRemover.className = 'btn btn-danger me-2';
    }
}

function calcular() {
    // Coletar dados dos campos
    const data = {
        numeroVias: numeroVias,
        stakesEditaveis: stakesEditaveis,
        stakeFixoEditado: stakeFixoEditado
    };
    
    // Coletar odds e cashbacks
    for (let i = 0; i < numeroVias; i++) {
        const letra = letras[i];
        const oddElement = document.getElementById(`odd${letra}`);
        const cbElement = document.getElementById(`cb${letra}`);
        
        if (oddElement && cbElement) {
            data[`odd${letra}`] = parseFloat(oddElement.value) || 0;
            data[`cb${letra}`] = parseFloat(cbElement.value) || 0;
        }
    }
    
    // Stake A (apenas se não estiver em modo dinâmico)
    const stakeAElement = document.getElementById('stakeA');
    if (stakeAElement && !stakeFixoEditado) {
        data.stakeA = parseFloat(stakeAElement.value) || 0;
    }
    
    // Verificar se temos dados suficientes
    let temDadosSuficientes = false;
    
    if (stakeFixoEditado && stakesEditaveis[stakeFixoEditado]) {
        // Modo dinâmico: verificar se temos a stake editada e odds
        temDadosSuficientes = stakesEditaveis[stakeFixoEditado] > 0;
        for (let i = 0; i < numeroVias; i++) {
            const letra = letras[i];
            if (data[`odd${letra}`] <= 0) {
                temDadosSuficientes = false;
                break;
            }
        }
    } else {
        // Modo tradicional: verificar stake A e odds
        temDadosSuficientes = data.stakeA > 0;
        for (let i = 0; i < numeroVias; i++) {
            const letra = letras[i];
            if (data[`odd${letra}`] <= 0) {
                temDadosSuficientes = false;
                break;
            }
        }
    }
    
    if (!temDadosSuficientes) {
        document.getElementById('resultado').innerHTML = '<p class="text-muted text-center">Preencha as odds e ao menos uma stake para calcular.</p>';
        return;
    }
    
    // Fazer requisição para o backend
    fetch('/calcular', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        exibirResultados(result);
    })
    .catch(error => {
        console.error('Erro:', error);
        document.getElementById('resultado').innerHTML = '<p class="text-danger text-center">Erro ao calcular. Tente novamente.</p>';
    });
}

function exibirResultados(res) {
    let lucroClass = res.lucro >= 0 ? 'profit' : 'loss';
    let roiClass = res.roi >= 0 ? 'profit' : 'loss';

    // Atualizar valores diretamente nos campos das vias
    for (let i = 0; i < numeroVias; i++) {
        const letra = letras[i];
        const stake = res[`stake${letra}`];
        const cashback = res[`cb${letra}`];
        const isStakeFixo = stakeFixoEditado === letra;
        
        // Atualizar campo de stake
        const stakeInput = document.getElementById(`stake${letra}`);
        if (stakeInput) {
            stakeInput.value = stake !== null && stake !== undefined ? stake.toFixed(2) : '';
            
            // Aplicar estilo visual para stake fixa
            if (isStakeFixo) {
                stakeInput.classList.add('bg-warning', 'text-dark');
                stakeInput.title = 'Esta é a stake base para o cálculo';
            } else {
                stakeInput.classList.remove('bg-warning', 'text-dark');
                stakeInput.title = 'Edite para recalcular as outras stakes';
            }
        }
        
        // Atualizar valor do cashback
        const cbValueElement = document.getElementById(`cbValue${letra}`);
        if (cbValueElement) {
            cbValueElement.textContent = cashback !== null && cashback !== undefined ? cashback.toFixed(2) : '0.00';
        }
        
        // Atualizar indicador visual no header do card
        const cardHeader = stakeInput?.closest('.card')?.querySelector('.card-header h6');
        if (cardHeader) {
            if (isStakeFixo) {
                cardHeader.innerHTML = `📊 Via ${letra} 🔒`;
                cardHeader.closest('.card-header').classList.add('bg-warning', 'text-dark');
                cardHeader.closest('.card-header').classList.remove('bg-success');
            } else {
                cardHeader.innerHTML = `📊 Via ${letra}`;
                cardHeader.closest('.card-header').classList.remove('bg-warning', 'text-dark');
                cardHeader.closest('.card-header').classList.add('bg-success');
            }
        }
    }

    // Área de resultados simplificada - apenas totais
    const botoesControle = `
        <div class="text-center mb-3">
            <button class="btn btn-outline-secondary btn-sm me-2" onclick="resetarParaAutomatico()">
                🔄 Modo Automático (Stake A)
            </button>
            <button class="btn btn-outline-info btn-sm" onclick="limparStakesEditaveis()">
                🧹 Limpar Stakes Editadas
            </button>
        </div>
    `;

    // Resultado final simplificado
    const resultadoHtml = `
        ${botoesControle}
        <hr>
        <div class="text-center mt-3">
            <div class="row justify-content-center">
                <div class="col-md-4 mb-2">
                    <div class="result-card p-3 bg-dark rounded">
                        <h5 class="text-white">💰 Lucro líquido</h5>
                        <h4 class="${lucroClass}">R$ ${res.lucro.toFixed(2)}</h4>
                    </div>
                </div>
                <div class="col-md-4 mb-2">
                    <div class="result-card p-3 bg-dark rounded">
                        <h5 class="text-white">📈 ROI</h5>
                        <h4 class="${roiClass}">${res.roi.toFixed(2)}%</h4>
                    </div>
                </div>
                <div class="col-md-4 mb-2">
                    <div class="result-card p-3 bg-dark rounded">
                        <h5 class="text-white">💵 Total Investido</h5>
                        <h4 class="text-info">R$ ${res.total_invested.toFixed(2)}</h4>
                    </div>
                </div>
            </div>
            ${res.message ? `<p class="text-info mt-3">${res.message}</p>` : ''}
            ${res.lucro > 0 ? '<p class="text-success mt-2">✅ Arbitragem com lucro garantido!</p>' : ''}
            ${res.modo_dinamico ? '<p class="text-warning mt-2">⚡ Modo Dinâmico Ativo - Stakes recalculadas automaticamente</p>' : ''}
        </div>
    `;

    document.getElementById('resultado').innerHTML = resultadoHtml;
    
    // Atualizar valores de referência
    for (let i = 0; i < numeroVias; i++) {
        const letra = letras[i];
        ultimosValoresStakes[letra] = res[`stake${letra}`];
    }
}

function editarStake(letra, valor) {
    const valorNumerico = parseFloat(valor);
    
    if (!isNaN(valorNumerico) && valorNumerico > 0) {
        // Definir esta stake como a fixa
        stakeFixoEditado = letra;
        stakesEditaveis[letra] = valorNumerico;
        
        // Limpar o campo Stake A se não for a via A
        if (letra !== 'A') {
            const stakeAElement = document.getElementById('stakeA');
            if (stakeAElement) {
                stakeAElement.value = '';
            }
        }
        
        // Recalcular com debounce
        clearTimeout(window.debounceTimer);
        window.debounceTimer = setTimeout(() => {
            calcular();
        }, 300);
    } else {
        // Se valor inválido, remover da lista de editáveis
        if (stakeFixoEditado === letra) {
            stakeFixoEditado = null;
        }
        delete stakesEditaveis[letra];
    }
}

function resetarParaAutomatico() {
    stakesEditaveis = {};
    stakeFixoEditado = null;
    ultimosValoresStakes = {};
    
    // Limpar campos de stakes editáveis
    for (let i = 0; i < numeroVias; i++) {
        const letra = letras[i];
        const stakeElement = document.getElementById(`stakeEditavel${letra}`);
        if (stakeElement) {
            stakeElement.value = '';
        }
    }
    
    calcular();
}

function limparStakesEditaveis() {
    stakesEditaveis = {};
    stakeFixoEditado = null;
    ultimosValoresStakes = {};
    
    // Manter apenas o resultado atual sem recalcular
    const resultadoElement = document.getElementById('resultado');
    if (resultadoElement.innerHTML.includes('stake')) {
        // Se há resultados, apenas remover indicadores visuais
        const stakesEditaveis = document.querySelectorAll('.stake-editavel');
        stakesEditaveis.forEach(input => {
            input.classList.remove('bg-warning', 'text-dark');
        });
        
        // Remover ícones de lock
        const highlights = document.querySelectorAll('.highlight');
        highlights.forEach(highlight => {
            highlight.classList.remove('border-warning');
            const h5 = highlight.querySelector('h5');
            if (h5) {
                h5.innerHTML = h5.innerHTML.replace(' 🔒', '');
            }
        });
        
        // Atualizar mensagem
        const infoMsg = document.querySelector('.text-warning');
        if (infoMsg && infoMsg.textContent.includes('Modo Dinâmico')) {
            infoMsg.remove();
        }
    }
}