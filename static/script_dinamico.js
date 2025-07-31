// Variáveis globais
let numeroVias = 2;
const letras = ['A', 'B', 'C', 'D', 'E'];
let stakesEditaveis = {};
let modoEdicao = false;

// Inicializar a página
document.addEventListener('DOMContentLoaded', function() {
    gerarCampos();
    atualizarContador();
    atualizarBotoes();
});

function gerarCampos() {
    const container = document.getElementById('campos-container');
    container.innerHTML = '';
    
    for (let i = 0; i < numeroVias; i++) {
        const letra = letras[i];
        const col = document.createElement('div');
        col.className = 'col-md-6 mb-3';
        
        col.innerHTML = `
            <div class="card bg-dark text-white">
                <div class="card-header bg-success text-center">
                    <h6 class="mb-0">📊 Via ${letra}</h6>
                </div>
                <div class="card-body">
                    <div class="input-group mb-2">
                        <span class="input-group-text">Odd ${letra}</span>
                        <input type="number" class="form-control" id="odd${letra}" step="0.01" oninput="calcular()" placeholder="Ex: 2.50">
                    </div>
                    <div class="input-group">
                        <span class="input-group-text">Cashback ${letra} (%)</span>
                        <input type="number" class="form-control" id="cb${letra}" step="0.01" oninput="calcular()" placeholder="Ex: 10">
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(col);
    }
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
        modoEdicao: modoEdicao,
        stakesEditaveis: stakesEditaveis
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
    
    // Stake A
    const stakeAElement = document.getElementById('stakeA');
    if (stakeAElement) {
        data.stakeA = parseFloat(stakeAElement.value) || 0;
    }
    
    // Verificar se temos dados suficientes
    let temDadosSuficientes = data.stakeA > 0;
    for (let i = 0; i < numeroVias; i++) {
        const letra = letras[i];
        if (data[`odd${letra}`] <= 0) {
            temDadosSuficientes = false;
            break;
        }
    }
    
    if (!temDadosSuficientes) {
        document.getElementById('resultado').innerHTML = '<p class="text-muted text-center">Preencha ao menos Odd A, Odd B e Stake A para calcular.</p>';
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

    // Gerar cards de resultado com stakes EDITÁVEIS
    let cardsHtml = '<div class="row text-center">';
    
    for (let i = 0; i < numeroVias; i++) {
        const letra = letras[i];
        const stake = res[`stake${letra}`];
        const cashback = res[`cb${letra}`];

        cardsHtml += `
            <div class="col-md-${12/Math.min(numeroVias, 4)} mb-3">
                <div class="highlight">
                    <h5>Via ${letra}</h5>
                    <div class="input-group mb-2">
                        <span class="input-group-text">Stake:</span>
                        <input type="number" 
                               class="form-control stake-editavel" 
                               id="stakeEditavel${letra}" 
                               value="${stake !== null && stake !== undefined ? stake.toFixed(2) : ''}"
                               step="0.01" 
                               oninput="editarStake('${letra}', this.value)"
                               ${letra === 'A' ? 'disabled title="Stake A é controlado pelo campo principal"' : ''}>
                        <span class="input-group-text">R$</span>
                    </div>
                    <p><strong>Cashback:</strong> R$ ${cashback !== null && cashback !== undefined ? cashback.toFixed(2) : '---'}</p>
                </div>
            </div>
        `;
    }
    
    cardsHtml += '</div>';

    // Botão para resetar para modo automático
    const resetButton = Object.keys(stakesEditaveis).length > 0 ? 
        '<button class="btn btn-outline-secondary btn-sm mb-3" onclick="resetarParaAutomatico()">🔄 Resetar para Cálculo Automático</button>' : '';

    // Resultado final
    const resultadoHtml = `
        ${resetButton}
        ${cardsHtml}
        <hr>
        <div class="text-center mt-3">
            <h5><span class="label-resultado">💰 Lucro líquido:</span> <strong class="${lucroClass}">R$ ${res.lucro.toFixed(2)}</strong></h5>
            <h5><span class="label-resultado">📈 ROI:</span> <strong class="${roiClass}">${res.roi.toFixed(2)}%</strong></h5>
            ${res.message ? `<p class="text-danger mt-2">${res.message}</p>` : ''}
            ${res.lucro > 0 ? '<p class="text-success mt-2">✅ Arbitragem com lucro garantido!</p>' : ''}
            ${Object.keys(stakesEditaveis).length > 0 ? '<p class="text-info mt-2">📝 Modo de edição ativo - Stakes ajustados manualmente</p>' : ''}
        </div>
    `;

    document.getElementById('resultado').innerHTML = resultadoHtml;
}

function editarStake(letra, valor) {
    if (letra === 'A') return; // Stake A não pode ser editado aqui
    
    const valorNumerico = parseFloat(valor);
    
    if (!isNaN(valorNumerico) && valorNumerico > 0) {
        stakesEditaveis[letra] = valorNumerico;
        modoEdicao = true;
        
        // Recalcular com o novo stake
        clearTimeout(window.debounceTimer);
        window.debounceTimer = setTimeout(() => {
            calcular();
        }, 300); // Debounce para evitar muitas requisições
    } else {
        // Se valor inválido, remover da lista de editáveis
        delete stakesEditaveis[letra];
        if (Object.keys(stakesEditaveis).length === 0) {
            modoEdicao = false;
        }
    }
}

function resetarParaAutomatico() {
    stakesEditaveis = {};
    modoEdicao = false;
    calcular();
}