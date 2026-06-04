// Estado global
let currentSessionId = null;
let websocket = null;
let possessionChart = null;
let passesChart = null;
let timelineChart = null;

// Gráficos para la sección de resultados
let resultsPossessionChart = null;
let resultsPassesChart = null;
let resultsTimelineChart = null;

// Estado del chatbot de alertas
let chatbotOpen = false;
let unreadAlerts = 0;
let alertHistory = [];
let attackDirectionState = null;
let jobsPollingInterval = null;

function getApiMode() {
    const host = (window.location.hostname || '').toLowerCase();
    if (host.includes('localhost') || host.includes('127.0.0.1')) return 'legacy';
    if (host.includes('run.app')) return 'jobs';
    return 'legacy';
}

async function safeFetchJson(response) {
    const raw = await response.text();
    const trimmed = (raw || '').trim();
    if (trimmed.startsWith('<')) {
        throw new Error(`Respuesta no JSON (${response.status}). El backend devolvió HTML.`);
    }
    try {
        return JSON.parse(trimmed || '{}');
    } catch (err) {
        throw new Error(`No se pudo parsear JSON (${response.status}): ${err.message}`);
    }
}

// Función para reiniciar la interfaz
function resetInterface() {
    // Cerrar WebSocket si existe
    if (websocket) {
        websocket.close();
        websocket = null;
    }
    if (jobsPollingInterval) {
        clearInterval(jobsPollingInterval);
        jobsPollingInterval = null;
    }
    
    // Resetear session ID
    currentSessionId = null;
    
    // Limpiar gráficos
    if (possessionChart) {
        possessionChart.destroy();
        possessionChart = null;
    }
    if (passesChart) {
        passesChart.destroy();
        passesChart = null;
    }
    if (timelineChart) {
        timelineChart.destroy();
        timelineChart = null;
    }
    if (resultsPossessionChart) {
        resultsPossessionChart.destroy();
        resultsPossessionChart = null;
    }
    if (resultsPassesChart) {
        resultsPassesChart.destroy();
        resultsPassesChart = null;
    }
    if (resultsTimelineChart) {
        resultsTimelineChart.destroy();
        resultsTimelineChart = null;
    }
    
    // Mostrar sección de upload, ocultar progreso y resultados
    document.getElementById('upload-section').style.display = 'block';
    document.getElementById('progress-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'none';
    
    // Limpiar formularios
    const fileInput = document.getElementById('videoFile');
    if (fileInput) fileInput.value = '';
    
    const urlInput = document.getElementById('videoUrl');
    if (urlInput) urlInput.value = '';
    
    const fileInfo = document.getElementById('file-info');
    if (fileInfo) fileInfo.style.display = 'none';
    
    const statusDiv = document.getElementById('upload-status');
    if (statusDiv) statusDiv.innerHTML = '';
    
    // Limpiar canvas de video
    const videoCanvas = document.getElementById('video-canvas');
    if (videoCanvas) {
        const ctx = videoCanvas.getContext('2d');
        ctx.clearRect(0, 0, videoCanvas.width, videoCanvas.height);
    }
    
    // Limpiar progress bar
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = '0%';
        progressBar.textContent = '0%';
    }
    
    // Limpiar textos de progreso
    const progressText = document.getElementById('progress-text');
    if (progressText) progressText.textContent = 'Esperando inicio...';
    
    const currentFrame = document.getElementById('current-frame');
    if (currentFrame) currentFrame.textContent = '0';
    
    const totalFrames = document.getElementById('total-frames');
    if (totalFrames) totalFrames.textContent = '0';
    
    // Ocultar y resetear chatbot
    const chatbot = document.getElementById('alert-chatbot');
    const toggleBtn = document.getElementById('chatbot-toggle-btn');
    if (chatbot) chatbot.style.display = 'none';
    if (toggleBtn) toggleBtn.style.display = 'none';
    chatbotOpen = false;
    unreadAlerts = 0;
    alertHistory = [];
    
    console.log('Interface reset - ready for new analysis');
}

// File selection handler
document.addEventListener('DOMContentLoaded', function() {
    // Event listener para el logo
    const brandLogo = document.getElementById('brand-logo');
    if (brandLogo) {
        brandLogo.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Confirmar si hay un análisis en curso
            if (currentSessionId && websocket) {
                if (confirm('¿Estás seguro de que quieres cancelar el análisis actual y volver al inicio?')) {
                    resetInterface();
                }
            } else {
                resetInterface();
            }
        });
    }
    console.log('DOM loaded, initializing file handlers...');
    
    const fileInput = document.getElementById('videoFile');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const fileUploadZone = document.getElementById('fileUploadZone');
    
    console.log('Elements found:', {
        fileInput: !!fileInput,
        fileInfo: !!fileInfo,
        fileName: !!fileName,
        fileUploadZone: !!fileUploadZone
    });
    
    if (!fileInput || !fileUploadZone) {
        console.error('Missing required elements!');
    } else {
        fileInput.addEventListener('change', function(e) {
            console.log('File selected:', this.files);
            if (this.files && this.files[0]) {
                fileName.textContent = this.files[0].name;
                fileInfo.style.display = 'block';
                console.log('File info displayed');
            }
        });
    }

    const applyDirBtn = document.getElementById('attack-direction-apply-btn');
    const autoDirBtn = document.getElementById('attack-direction-auto-btn');
    if (applyDirBtn) applyDirBtn.addEventListener('click', applyAttackDirectionControl);
    if (autoDirBtn) autoDirBtn.addEventListener('click', clearAttackDirectionManualOverride);

    renderAttackDirectionState();

    if (!fileInput || !fileUploadZone) {
        return;
    }
    
    // Drag and drop
    fileUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileUploadZone.classList.add('dragover');
    });
    
    fileUploadZone.addEventListener('dragleave', () => {
        fileUploadZone.classList.remove('dragover');
    });
    
    fileUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        fileUploadZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            fileName.textContent = files[0].name;
            fileInfo.style.display = 'block';
            console.log('File dropped:', files[0].name);
        }
    });
    
    console.log('File handlers initialized successfully');
});

// Actualizar placeholder según tipo de URL
function updateUrlPlaceholder() {
    const urlInput = document.getElementById('videoUrl');
    const helpText = document.getElementById('urlHelpText');
    const sourceType = document.getElementById('urlSourceType').value;
    
    const placeholders = {
        'youtube': 'https://www.youtube.com/watch?v=... or https://youtu.be/...',
        'hls': 'https://example.com/stream.m3u8',
        'rtmp': 'rtmp://example.com/live/stream',
        'veo': 'https://veo.co/matches/...'
    };
    
    const helpTexts = {
        'youtube': 'Paste YouTube video URL or live stream link',
        'hls': 'Enter HLS stream URL (.m3u8)',
        'rtmp': 'Enter RTMP stream URL',
        'veo': 'Enter Veo match URL'
    };
    
    urlInput.placeholder = placeholders[sourceType] || placeholders['youtube'];
    helpText.innerHTML = '<i class="fas fa-info-circle"></i> ' + (helpTexts[sourceType] || helpTexts['youtube']);
}

// Analizar desde URL
async function analyzeFromUrl() {
    console.log('analyzeFromUrl called');
    
    const urlInput = document.getElementById('videoUrl');
    const sourceType = document.getElementById('urlSourceType').value;
    const url = urlInput.value.trim();
    
    console.log('URL:', url, 'Type:', sourceType);
    
    if (!url) {
        alert('Please enter a video URL');
        return;
    }
    
    const statusDiv = document.getElementById('upload-status');
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Connecting to stream...</div>';
    
    try {
        const apiMode = getApiMode();
        if (apiMode === 'jobs') {
            const response = await fetch('/jobs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    input_uri: url
                })
            });
            const data = await safeFetchJson(response);
            currentSessionId = data.id || data.job_id || null;
            if (!currentSessionId) {
                throw new Error('No se recibió job_id en la respuesta /jobs');
            }
            statusDiv.innerHTML = '<div class="alert alert-success"><i class="fas fa-check-circle me-2"></i>Job enviado correctamente</div>';
            document.getElementById('upload-section').style.display = 'none';
            document.getElementById('progress-section').style.display = 'block';
            initializeChatbot();
            startJobsPolling(currentSessionId);
            return;
        }

        console.log('Sending request to /api/analyze/url');
        const response = await fetch('/api/analyze/url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                source_type: sourceType
            })
        });
        
        const data = await safeFetchJson(response);
        console.log('Response:', data);
        
        if (data.success) {
            currentSessionId = data.session_id;
            statusDiv.innerHTML = '<div class="alert alert-success"><i class="fas fa-check-circle me-2"></i>Stream connected successfully!</div>';
            fetchAttackDirectionState();
            
            // Conectar WebSocket
            connectWebSocket();
            
            // Mostrar sección de progreso
            document.getElementById('upload-section').style.display = 'none';
            document.getElementById('progress-section').style.display = 'block';
            
            // Inicializar chatbot de alertas
            initializeChatbot();
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Error: ${data.error}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Error: ${error.message}</div>`;
    }
}

// Subir video
async function uploadVideo() {
    console.log('uploadVideo called');
    
    const fileInput = document.getElementById('videoFile');
    const file = fileInput.files[0];
    
    console.log('File:', file);
    
    if (!file) {
        alert('Por favor selecciona un video');
        return;
    }
    
    const uploadBtn = document.getElementById('uploadBtn');
    const statusDiv = document.getElementById('upload-status');
    
    uploadBtn.disabled = true;
    statusDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Subiendo video...</div>';
    
    try {
        if (getApiMode() === 'jobs') {
            // Step 1: get a signed GCS URL (avoids Cloud Run's 32MB body limit)
            statusDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Preparando subida...</div>';
            const urlResp = await fetch(`/jobs/upload-url?filename=${encodeURIComponent(file.name)}`);
            const urlData = await safeFetchJson(urlResp);
            if (!urlData.upload_url || !urlData.input_uri) throw new Error('No se recibió URL de subida');

            // Step 2: PUT directly to GCS — bypasses Cloud Run completely
            statusDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Subiendo video a la nube...</div>';
            const putResp = await fetch(urlData.upload_url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/octet-stream' },
                body: file
            });
            if (!putResp.ok) throw new Error(`Error subiendo a GCS: ${putResp.status}`);

            // Step 3: create the analysis job
            statusDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-spinner fa-spin me-2"></i>Creando job de análisis...</div>';
            const jobResp = await fetch('/jobs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input_uri: urlData.input_uri })
            });
            const jobData = await safeFetchJson(jobResp);
            currentSessionId = jobData.id || jobData.job_id || null;
            if (!currentSessionId) throw new Error('No se recibió job_id');

            statusDiv.innerHTML = '<div class="alert alert-success"><i class="fas fa-check-circle me-2"></i>Video subido. Analizando...</div>';
            document.getElementById('upload-section').style.display = 'none';
            document.getElementById('progress-section').style.display = 'block';
            initializeChatbot();
            startJobsPolling(currentSessionId);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        
        console.log('Uploading file to /api/upload');
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await safeFetchJson(response);
        console.log('Upload response:', data);
        
        if (data.success) {
            currentSessionId = data.session_id;
            statusDiv.innerHTML = '<div class="alert alert-success"><i class="fas fa-check-circle me-2"></i>Video subido correctamente</div>';
            fetchAttackDirectionState();
            
            // Conectar WebSocket
            connectWebSocket();
            
            // Iniciar análisis
            startAnalysis();
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Error: ${data.error}</div>`;
            uploadBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error in uploadVideo:', error);
        statusDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>Error: ${error.message}</div>`;
        uploadBtn.disabled = false;
    }
}

function startJobsPolling(jobId) {
    if (jobsPollingInterval) {
        clearInterval(jobsPollingInterval);
    }

    const progressText = document.getElementById('progress-text');
    const progressBarFill = document.getElementById('progressBarFill');
    const progressPercent = document.getElementById('progressPercent');

    const poll = async () => {
        try {
            const response = await fetch(`/jobs/${jobId}`);
            const data = await safeFetchJson(response);
            const status = (data.status || '').toLowerCase();

            if (status === 'pending') {
                if (progressText) progressText.textContent = 'Pendiente de ejecución...';
                if (progressBarFill) progressBarFill.style.width = '10%';
                if (progressPercent) progressPercent.textContent = '10%';
                return;
            }

            if (status === 'running') {
                try {
                    const partialResp = await fetch(`/jobs/${jobId}/partial`);
                    const partial = await safeFetchJson(partialResp);
                    if (partial.available) {
                        const batch = partial.batch_idx || 0;
                        if (progressText) progressText.textContent = `Procesando... lote ${batch + 1} completado`;
                        if (progressBarFill) progressBarFill.style.width = '60%';
                        if (progressPercent) progressPercent.textContent = `Lote ${batch + 1}`;
                        showResults(partial);
                        // Renderizar heatmaps parciales si están disponibles
                        if (partial.heatmap_team_0) {
                            const img0 = document.getElementById('heatmap-team-0');
                            if (img0) renderHeatmapToImg(partial.heatmap_team_0, img0);
                        }
                        if (partial.heatmap_team_1) {
                            const img1 = document.getElementById('heatmap-team-1');
                            if (img1) renderHeatmapToImg(partial.heatmap_team_1, img1);
                        }
                    } else {
                        if (progressText) progressText.textContent = 'Iniciando análisis...';
                        if (progressBarFill) progressBarFill.style.width = '20%';
                    }
                } catch (_) {
                    if (progressText) progressText.textContent = 'Procesando...';
                }
                return;
            }

            if (status === 'completed' || status === 'finished') {
                clearInterval(jobsPollingInterval);
                jobsPollingInterval = null;
                if (progressBarFill) progressBarFill.style.width = '100%';
                if (progressPercent) progressPercent.textContent = '100%';
                if (progressText) progressText.textContent = 'Completado';
                const resultsResp = await fetch(`/jobs/${jobId}/results`);
                const resultsData = await safeFetchJson(resultsResp);
                if (resultsData.result) {
                    const parsed = typeof resultsData.result === 'string' ? JSON.parse(resultsData.result) : resultsData.result;
                    const summary = parsed.summary || parsed;
                    const pct = summary.possession?.percent_by_team || {};
                    const secs = summary.possession?.seconds_by_team || {};
                    const passes = summary.passes?.by_team || {};
                    showResults({
                        total_seconds: summary.progress?.total_seconds || 0,
                        total_frames: summary.progress?.total_frames || 0,
                        possession_percent: [pct[0] || 0, pct[1] || 0],
                        possession_seconds: [secs[0] || 0, secs[1] || 0],
                        passes: [passes[0] || 0, passes[1] || 0],
                        alerts: summary.alerts || [],
                    });
                }
                return;
            }

            if (status === 'failed') {
                clearInterval(jobsPollingInterval);
                jobsPollingInterval = null;
                showError(data.error_message || 'El job falló');
            }
        } catch (err) {
            console.error('Error consultando estado de job:', err);
        }
    };

    poll();
    jobsPollingInterval = setInterval(poll, 2500);
}

// Conectar WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${currentSessionId}`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    websocket.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
    
    websocket.onclose = function() {
        console.log('WebSocket closed');
    };
}

// Manejar mensajes WebSocket
function handleWebSocketMessage(data) {
    console.log('WebSocket message:', data);
    
    if (data.type === 'status') {
        document.getElementById('progress-text').textContent = data.message;
    } else if (data.type === 'progress') {
        updateProgress(data);
        // Iniciar actualizaciones de heatmap cuando comienza el análisis
        if (!heatmapUpdateInterval && currentSessionId) {
            startHeatmapUpdates();
        }
    } else if (data.type === 'frame') {
        updateVideoFrame(data);
    } else if (data.type === 'batch_complete') {
        updateBatchComplete(data);
    } else if (data.type === 'alert') {
        handleAlert(data.alert);
    } else if (data.type === 'alerts') {
        const alerts = Array.isArray(data.alerts) ? data.alerts : [];
        alerts.forEach((alert) => handleAlert(alert));
    } else if (data.type === 'attack_direction') {
        attackDirectionState = data.state || null;
        renderAttackDirectionState();
    } else if (data.type === 'completed') {
        stopHeatmapUpdates();
        showResults(data.stats);
    } else if (data.type === 'error') {
        stopHeatmapUpdates();
        showError(data.message);
    }
}

// Actualizar frame del video
function updateVideoFrame(data) {
    const canvas = document.getElementById('videoCanvas');
    if (!canvas) {
        console.warn('Canvas element not found');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    const img = new Image();
    img.onload = function() {
        // Ajustar tamaño del canvas si es necesario
        if (canvas.width !== img.width || canvas.height !== img.height) {
            canvas.width = img.width;
            canvas.height = img.height;
        }
        
        // Dibujar imagen
        ctx.drawImage(img, 0, 0);
    };
    
    img.onerror = function() {
        console.error('Error loading frame image');
    };
    
    img.src = 'data:image/jpeg;base64,' + data.image;
    
    // Actualizar número de frame si está disponible
    if (data.frame_idx !== undefined) {
        const currentFrameEl = document.getElementById('current-frame');
        if (currentFrameEl) {
            currentFrameEl.textContent = data.frame_idx;
        }
    }
}

// Iniciar análisis
async function startAnalysis() {
    document.getElementById('upload-section').style.display = 'none';
    document.getElementById('progress-section').style.display = 'block';
    
    // Inicializar chatbot de alertas
    initializeChatbot();
    
    try {
        const response = await fetch(`/api/analyze/${currentSessionId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (!data.success) {
            showError(data.error);
        }
    } catch (error) {
        showError(error.message);
    }
}

// Actualizar progreso
function updateProgress(data) {
    const progressBarFill = document.getElementById('progressBarFill');
    const progressPercent = document.getElementById('progressPercent');
    const progressText = document.getElementById('progress-text');
    const currentFrame = document.getElementById('current-frame');
    const totalFrames = document.getElementById('total-frames');
    const currentBatch = document.getElementById('current-batch');
    
    progressBarFill.style.width = data.progress + '%';
    progressPercent.textContent = data.progress + '%';
    
    if (data.frame !== undefined) {
        currentFrame.textContent = data.frame;
    }
    
    if (data.total_frames !== undefined) {
        totalFrames.textContent = data.total_frames;
    }
    
    if (data.batch_idx !== undefined && currentBatch) {
        currentBatch.textContent = data.batch_idx + 1;
    }
    
    progressText.textContent = data.message || `Frame ${data.frame} / ${data.total_frames}`;
}

// Actualizar cuando se completa un batch
function updateBatchComplete(data) {
    const progressText = document.getElementById('progress-text');
    
    // Mostrar mensaje de batch completo
    if (data.message) {
        progressText.textContent = data.message;
    }
    
    // Actualizar estadísticas en tiempo real
    if (data.stats) {
        console.log('Stats recibidas:', data.stats);
        if (data.stats.attack_direction) {
            attackDirectionState = data.stats.attack_direction;
            renderAttackDirectionState();
        }
        updateLiveStats(data.stats);
        updateLiveCharts(data.stats);
        
        // Actualizar estadísticas espaciales si están disponibles
        if (data.stats.spatial) {
            console.log('Spatial stats:', data.stats.spatial);
            updateSpatialStats(data.stats.spatial);
        } else {
            console.warn('No spatial stats en este batch');
        }

    }
}

async function fetchAttackDirectionState() {
    if (!currentSessionId) return;
    try {
        const res = await fetch(`/api/attack-direction?session_id=${encodeURIComponent(currentSessionId)}`);
        const data = await res.json();
        if (data.success) {
            attackDirectionState = data.state || null;
            renderAttackDirectionState();
        }
    } catch (err) {
        console.warn('No se pudo obtener attack direction:', err);
    }
}

function renderAttackDirectionState() {
    const badge = document.getElementById('attack-direction-badge');
    const text = document.getElementById('attack-direction-state-text');
    const modeSel = document.getElementById('attack-direction-mode');
    const periodSel = document.getElementById('attack-direction-period');
    const team0Sel = document.getElementById('attack-direction-team0');
    if (!badge || !text || !modeSel || !periodSel || !team0Sel) return;

    const s = attackDirectionState || {
        mode: 'manual',
        period: 1,
        team_0_attacks_to: null,
        team_1_attacks_to: null,
        confidence: 0,
        source: 'manual_override'
    };

    badge.className = 'badge bg-primary';
    badge.textContent = 'mode: manual';
    text.textContent = `mode=${s.mode} | period=${s.period} | team_0_attacks_to=${s.team_0_attacks_to} | team_1_attacks_to=${s.team_1_attacks_to} | confidence=${(s.confidence || 0).toFixed(2)} | source=${s.source}`;

    modeSel.value = 'manual';
    periodSel.value = String(s.period || 1);
    if (s.team_0_attacks_to) {
        team0Sel.value = s.team_0_attacks_to;
    }
}

async function applyAttackDirectionControl() {
    if (!currentSessionId) return;
    const modeSel = document.getElementById('attack-direction-mode');
    const periodSel = document.getElementById('attack-direction-period');
    const team0Sel = document.getElementById('attack-direction-team0');
    if (!modeSel || !periodSel || !team0Sel) return;

    try {
        const response = await fetch('/api/attack-direction/manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                period: Number(periodSel.value || 1),
                team_0_attacks_to: team0Sel.value
            })
        });
        const data = await response.json();
        if (data.success) {
            attackDirectionState = data.state || null;
            renderAttackDirectionState();
        }
    } catch (err) {
        console.error('Error actualizando orientación de ataque:', err);
    }
}

async function clearAttackDirectionManualOverride() {
    if (!currentSessionId) return;
    try {
        const response = await fetch('/api/attack-direction/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId })
        });
        const data = await response.json();
        if (data.success) {
            attackDirectionState = data.state || null;
            renderAttackDirectionState();
        }
    } catch (err) {
        console.error('Error limpiando override manual:', err);
    }
}

// Actualizar gráficos en tiempo real
function updateLiveCharts(stats) {
    // Inicializar gráficos si no existen
    if (!possessionChart || !passesChart) {
        initializeCharts();
    }
    
    // Actualizar gráfico de posesión
    if (stats.possession_percent && possessionChart) {
        possessionChart.data.datasets[0].data = [
            stats.possession_percent[0] || 0,
            stats.possession_percent[1] || 0
        ];
        possessionChart.update('none');
    }
    
    // Actualizar gráfico de pases
    if (stats.passes && passesChart) {
        passesChart.data.datasets[0].data = [
            stats.passes[0] || 0,
            stats.passes[1] || 0
        ];
        passesChart.update('none');
    }
    
    // Actualizar estadísticas detalladas por equipo (sección LIVE)
    if (stats.possession_percent) {
        const elem0 = document.getElementById('live-possession-percent-0');
        const elem1 = document.getElementById('live-possession-percent-1');
        if (elem0) elem0.textContent = (stats.possession_percent[0] || 0).toFixed(1) + '%';
        if (elem1) elem1.textContent = (stats.possession_percent[1] || 0).toFixed(1) + '%';
        
        const bar0 = document.getElementById('live-possession-bar-0');
        const bar1 = document.getElementById('live-possession-bar-1');
        if (bar0) bar0.style.width = (stats.possession_percent[0] || 0) + '%';
        if (bar1) bar1.style.width = (stats.possession_percent[1] || 0) + '%';
    }
    
    if (stats.possession_seconds) {
        const time0 = document.getElementById('live-possession-time-0');
        const time1 = document.getElementById('live-possession-time-1');
        if (time0) time0.textContent = (stats.possession_seconds[0] || 0).toFixed(1) + 's';
        if (time1) time1.textContent = (stats.possession_seconds[1] || 0).toFixed(1) + 's';
    }
    
    if (stats.passes) {
        const passes0 = document.getElementById('live-passes-0');
        const passes1 = document.getElementById('live-passes-1');
        if (passes0) passes0.textContent = stats.passes[0] || 0;
        if (passes1) passes1.textContent = stats.passes[1] || 0;
    }
    
    // También actualizar las estadísticas finales (para cuando se complete)
    const finalPercent0 = document.getElementById('possession-percent-0');
    const finalPercent1 = document.getElementById('possession-percent-1');
    if (finalPercent0 && stats.possession_percent) finalPercent0.textContent = (stats.possession_percent[0] || 0).toFixed(1) + '%';
    if (finalPercent1 && stats.possession_percent) finalPercent1.textContent = (stats.possession_percent[1] || 0).toFixed(1) + '%';
    
    const finalBar0 = document.getElementById('possession-bar-0');
    const finalBar1 = document.getElementById('possession-bar-1');
    if (finalBar0 && stats.possession_percent) finalBar0.style.width = (stats.possession_percent[0] || 0) + '%';
    if (finalBar1 && stats.possession_percent) finalBar1.style.width = (stats.possession_percent[1] || 0) + '%';
    
    const finalTime0 = document.getElementById('possession-time-0');
    const finalTime1 = document.getElementById('possession-time-1');
    if (finalTime0 && stats.possession_seconds) finalTime0.textContent = (stats.possession_seconds[0] || 0).toFixed(1) + 's';
    if (finalTime1 && stats.possession_seconds) finalTime1.textContent = (stats.possession_seconds[1] || 0).toFixed(1) + 's';
    
    const finalPasses0 = document.getElementById('passes-0');
    const finalPasses1 = document.getElementById('passes-1');
    if (finalPasses0 && stats.passes) finalPasses0.textContent = stats.passes[0] || 0;
    if (finalPasses1 && stats.passes) finalPasses1.textContent = stats.passes[1] || 0;
}

// Actualizar estadísticas en vivo
function updateLiveStats(stats) {
    // Crear o actualizar panel de estadísticas en vivo
    let liveStatsDiv = document.getElementById('live-stats');
    
    if (!liveStatsDiv) {
        // Crear panel si no existe
        const progressSection = document.getElementById('progress-section');
        liveStatsDiv = document.createElement('div');
        liveStatsDiv.id = 'live-stats';
        liveStatsDiv.className = 'mt-4';
        liveStatsDiv.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0"><i class="fas fa-chart-line me-2"></i>Estadísticas en Tiempo Real</h5>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        <div class="col-md-3">
                            <div class="stat-box">
                                <i class="fas fa-users fa-2x text-primary mb-2"></i>
                                <div class="stat-label">Detecciones</div>
                                <div class="stat-value" id="live-detections">0</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-box">
                                <i class="fas fa-futbol fa-2x text-success mb-2"></i>
                                <div class="stat-label">Posesión</div>
                                <div class="stat-value" id="live-possession">-</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-box">
                                <i class="fas fa-bolt fa-2x text-warning mb-2"></i>
                                <div class="stat-label">Eventos</div>
                                <div class="stat-value" id="live-events">0</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="stat-box">
                                <i class="fas fa-tachometer-alt fa-2x text-info mb-2"></i>
                                <div class="stat-label">FPS Procesado</div>
                                <div class="stat-value" id="live-fps">0</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        progressSection.appendChild(liveStatsDiv);
    }
    
    // Actualizar valores
    if (stats.detections !== undefined) {
        document.getElementById('live-detections').textContent = stats.detections;
    }
    
    if (stats.possession_team !== undefined) {
        const possessionText = stats.possession_team >= 0 ? `Equipo ${stats.possession_team}` : 'Sin posesión';
        document.getElementById('live-possession').textContent = possessionText;
    }
    
    if (stats.events !== undefined) {
        document.getElementById('live-events').textContent = stats.events;
    }
    
    if (stats.fps_processing !== undefined) {
        document.getElementById('live-fps').textContent = stats.fps_processing + ' fps';
    }
}

// Mostrar resultados finales
function showResults(stats) {
    console.log('Mostrando resultados finales:', stats);

    document.getElementById('progress-section').style.display = 'none';
    document.getElementById('results-section').style.display = 'block';

    // Stats Overview
    document.getElementById('total-time').textContent = stats.total_seconds.toFixed(1) + 's';
    document.getElementById('total-frames-stat').textContent = stats.total_frames;
    document.getElementById('possession-stat-0').textContent = (stats.possession_percent[0] || 0).toFixed(1) + '%';
    document.getElementById('possession-stat-1').textContent = (stats.possession_percent[1] || 0).toFixed(1) + '%';

    // Mostrar botón de resumen de heatmaps
    const summaryBtnContainer = document.getElementById('heatmap-summary-btn-container');
    if (summaryBtnContainer) {
        summaryBtnContainer.style.display = 'block';
    }
    const finalSummaryBtnContainer = document.getElementById('final-heatmap-summary-btn-container');
    if (finalSummaryBtnContainer) {
        finalSummaryBtnContainer.style.display = 'block';
    }

    // Actualizar estadísticas espaciales finales si están disponibles
    if (stats.spatial) {
        console.log('Stats espaciales finales:', stats.spatial);
        updateSpatialStats(stats.spatial);

        // Mostrar zonas dominantes si están disponibles
        if (stats.spatial.zone_percentages) {
            console.log('Actualizando zonas con datos finales');
            updateTopZones(0, stats.spatial.zone_percentages[0] || stats.spatial.zone_percentages['0'] || []);
            updateTopZones(1, stats.spatial.zone_percentages[1] || stats.spatial.zone_percentages['1'] || []);
        }
    }

    // Posesión
    const p0 = (stats.possession_percent && stats.possession_percent[0]) || 0;
    const p1 = (stats.possession_percent && stats.possession_percent[1]) || 0;

    document.getElementById('possession-percent-0').textContent = p0.toFixed(1) + '%';
    document.getElementById('possession-percent-1').textContent = p1.toFixed(1) + '%';

    document.getElementById('possession-bar-0').style.width = p0 + '%';
    document.getElementById('possession-bar-1').style.width = p1 + '%';

    // Tiempo
    const t0 = (stats.possession_seconds && stats.possession_seconds[0]) || 0;
    const t1 = (stats.possession_seconds && stats.possession_seconds[1]) || 0;

    document.getElementById('possession-time-0').textContent = t0.toFixed(1) + 's';
    document.getElementById('possession-time-1').textContent = t1.toFixed(1) + 's';

    // Pases
    const passes0 = (stats.passes && stats.passes[0]) || 0;
    const passes1 = (stats.passes && stats.passes[1]) || 0;

    document.getElementById('passes-0').textContent = passes0;
    document.getElementById('passes-1').textContent = passes1;

    // Inicializar gráficos de resultados
    initializeResultsCharts();

    // Actualizar gráficos
    if (resultsPossessionChart) {
        console.log('Actualizando gráfico de posesión:', [p0, p1]);
        resultsPossessionChart.data.datasets[0].data = [p0, p1];
        resultsPossessionChart.update();
    }

    if (resultsPassesChart) {
        console.log('Actualizando gráfico de pases:', [passes0, passes1]);
        resultsPassesChart.data.datasets[0].data = [passes0, passes1];
        resultsPassesChart.update();
    }

    // Timeline
    if (stats.timeline && stats.timeline.length > 0 && resultsTimelineChart) {
        console.log('Actualizando timeline con', stats.timeline.length, 'segmentos');
        updateResultsTimelineChart(stats.timeline, stats.total_frames);
    } else {
        console.log('Timeline vacío o no inicializado');
    }

    // IMPORTANTE: Actualizar heatmaps cuando el análisis termina.
    // Reintento para asegurar disponibilidad de archivos.
    if (currentSessionId) {
        setTimeout(() => {
            updateHeatmapImages();
            updateFinalHeatmapImages();
            setTimeout(() => updateFinalHeatmapImages(), 2000);
        }, 1000);
    }
}

// Inicializar gráficos
function initializeCharts() {
    if (possessionChart) return; // Ya inicializados
    
    // Gráfico de posesión (circular)
    const possessionCtx = document.getElementById('possessionChart').getContext('2d');
    possessionChart = new Chart(possessionCtx, {
        type: 'doughnut',
        data: {
            labels: ['Equipo 0', 'Equipo 1'],
            datasets: [{
                data: [0, 0],
                backgroundColor: ['#00c851', '#ff4444'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.parsed.toFixed(1) + '%';
                        }
                    }
                }
            }
        }
    });
    
    // Gráfico de pases (barras)
    const passesCtx = document.getElementById('passesChart').getContext('2d');
    passesChart = new Chart(passesCtx, {
        type: 'bar',
        data: {
            labels: ['Equipo 0', 'Equipo 1'],
            datasets: [{
                label: 'Pases Completados',
                data: [0, 0],
                backgroundColor: ['#00c851', '#ff4444'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
    
    // Gráfico de timeline
    const timelineCtx = document.getElementById('timelineChart').getContext('2d');
    timelineChart = new Chart(timelineCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Timeline de Posesión',
                data: [],
                backgroundColor: []
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const team = context.dataset.backgroundColor[context.dataIndex] === '#00c851' ? 'Equipo 0' : 'Equipo 1';
                            return team + ': ' + context.parsed.x + ' frames';
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true
                }
            }
        }
    });
}

// Inicializar gráficos para resultados finales
function initializeResultsCharts() {
    if (resultsPossessionChart) return; // Ya inicializados

    // Gráfico de posesión (circular)
    const possessionCtx = document.getElementById('resultsPossessionChart')?.getContext('2d');
    if (!possessionCtx) return;

    resultsPossessionChart = new Chart(possessionCtx, {
        type: 'doughnut',
        data: {
            labels: ['Equipo 0', 'Equipo 1'],
            datasets: [{
                data: [50, 50],
                backgroundColor: ['#00c851', '#ff4444'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.parsed.toFixed(1) + '%';
                        }
                    }
                }
            }
        }
    });

    // Gráfico de pases (barras)
    const passesCtx = document.getElementById('resultsPassesChart')?.getContext('2d');
    if (passesCtx) {
        resultsPassesChart = new Chart(passesCtx, {
            type: 'bar',
            data: {
                labels: ['Equipo 0', 'Equipo 1'],
                datasets: [{
                    label: 'Pases Completados',
                    data: [0, 0],
                    backgroundColor: ['#00c851', '#ff4444'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    // Gráfico de timeline
    const timelineCtx = document.getElementById('resultsTimelineChart')?.getContext('2d');
    if (timelineCtx) {
        resultsTimelineChart = new Chart(timelineCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Timeline de Posesión',
                    data: [],
                    backgroundColor: []
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const team = context.dataset.backgroundColor[context.dataIndex] === '#00c851' ? 'Equipo 0' : 'Equipo 1';
                                return team + ': ' + context.parsed.x + ' frames';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        stacked: true
                    },
                    y: {
                        stacked: true
                    }
                }
            }
        });
    }
}

// Actualizar timeline de resultados
function updateResultsTimelineChart(timeline, totalFrames) {
    if (!resultsTimelineChart || !timeline || timeline.length === 0) {
        console.log('Timeline vacío o gráfico no inicializado');
        return;
    }

    const labels = [];
    const data = [];
    const colors = [];

    timeline.forEach((segment, i) => {
        const [start, end, team] = segment;
        const duration = end - start;

        labels.push(`Seg ${i + 1}`);
        data.push(duration);
        colors.push(team === 0 ? '#00c851' : '#ff4444');
    });

    resultsTimelineChart.data.labels = labels;
    resultsTimelineChart.data.datasets[0].data = data;
    resultsTimelineChart.data.datasets[0].backgroundColor = colors;
    resultsTimelineChart.update();
}

// Mostrar error
function showError(message) {
    document.getElementById('progress-section').style.display = 'none';
    document.getElementById('upload-section').style.display = 'block';
    document.getElementById('uploadBtn').disabled = false;
    
    const statusDiv = document.getElementById('upload-status');
    statusDiv.innerHTML = `<div class="alert alert-danger">Error: ${message}</div>`;
}

// Actualizar estadísticas espaciales
function updateSpatialStats(spatial) {
    console.log('updateSpatialStats llamada con:', spatial);
    
    if (!spatial) {
        console.warn('No hay datos espaciales');
        return;
    }
    
    // Mostrar sección de heatmaps
    const heatmapsSection = document.getElementById('spatial-heatmaps-section');
    if (heatmapsSection) {
        console.log('Mostrando sección de heatmaps');
        heatmapsSection.style.display = 'block';
    } else {
        console.error('No se encontró el elemento spatial-heatmaps-section');
    }
    
    // Actualizar estado de calibración
    const calibrationStatus = document.getElementById('calibration-status');
    const spatialStatusMessage = document.getElementById('spatial-status-message');
    
    if (calibrationStatus) {
        if (spatial.calibration_valid) {
            calibrationStatus.innerHTML = '<i class="fas fa-check-circle"></i> Calibrated';
            calibrationStatus.className = 'badge bg-success';
            if (spatialStatusMessage) {
                spatialStatusMessage.innerHTML = '<small>✅ Field calibration successful! Heatmaps are being generated.</small>';
            }
        } else {
            calibrationStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> No Calibration';
            calibrationStatus.className = 'badge bg-warning';
            if (spatialStatusMessage) {
                spatialStatusMessage.innerHTML = '<small>⚠️ Field lines not detected. Heatmaps require visible field markings.</small>';
            }
        }
    }
    
    // Actualizar info de partición
    const partitionTypeText = document.getElementById('partition-type-text');
    if (partitionTypeText) {
        partitionTypeText.textContent = spatial.partition_type || 'thirds_lanes';
    }
    
    const numZonesText = document.getElementById('num-zones-text');
    if (numZonesText) {
        numZonesText.textContent = spatial.num_zones || 9;
    }
    
    // Actualizar heatmaps (usando sessionId actual)
    if (currentSessionId && spatial.calibration_valid) {
        updateHeatmapImages();
    }
    
    // Mostrar top zonas (soporta múltiples formatos de payload y fallback)
    updateTopZonesFromSpatial(0, spatial);
    updateTopZonesFromSpatial(1, spatial);
}

function getTeamZonePercentagesFromSpatial(teamId, spatial) {
    if (!spatial) return null;

    const zp = spatial.zone_percentages || {};
    const pbz = spatial.possession_by_zone || {};
    const sumArray = (arr) => arr.reduce((acc, val) => acc + (Number(val) || 0), 0);
    const hasSignal = (arr) => sumArray(arr) > 1e-6;

    const candidates = [
        zp[teamId],
        zp[String(teamId)],
        zp[`team_${teamId}`],
        zp[`team${teamId}`],
        pbz[teamId],
        pbz[String(teamId)],
        pbz[`team_${teamId}`],
        pbz[`team${teamId}`]
    ];

    for (const candidate of candidates) {
        if (Array.isArray(candidate)) {
            const numeric = candidate.map((v) => Number(v) || 0);
            // Si viene desde possession_by_zone (frames), normalizar a porcentajes
            const isPossessionFramesCandidate = (
                candidate === pbz[teamId] ||
                candidate === pbz[String(teamId)] ||
                candidate === pbz[`team_${teamId}`] ||
                candidate === pbz[`team${teamId}`]
            );
            const sum = sumArray(numeric);
            if (sum > 0 && isPossessionFramesCandidate) {
                return numeric.map((v) => (v / sum) * 100);
            }
            // Si este candidato no tiene señal (todo 0), seguimos buscando fallback.
            if (!hasSignal(numeric)) {
                continue;
            }
            return numeric;
        }
    }
    return null;
}

function updateTopZonesFromSpatial(teamId, spatial) {
    const zonePercentages = getTeamZonePercentagesFromSpatial(teamId, spatial);
    if (zonePercentages) {
        updateTopZones(teamId, zonePercentages);
    }
}

// Renderizar heatmap 2D (array de arrays) en un elemento <img> via canvas
function renderHeatmapToImg(grid, imgElement) {
    if (!grid || !grid.length) return;
    const rows = grid.length;
    const cols = grid[0].length;
    const canvas = document.createElement('canvas');
    canvas.width = cols * 8;
    canvas.height = rows * 8;
    const ctx = canvas.getContext('2d');

    // Fondo campo verde
    ctx.fillStyle = '#2d5016';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Heatmap (colormap: transparente→amarillo→rojo)
    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const v = Math.min(1, Math.max(0, grid[r][c]));
            if (v < 0.01) continue;
            const red = Math.round(255 * Math.min(1, v * 2));
            const green = Math.round(255 * Math.max(0, 1 - v * 2));
            ctx.fillStyle = `rgba(${red},${green},0,${0.3 + v * 0.65})`;
            ctx.fillRect(c * 8, r * 8, 8, 8);
        }
    }

    // Líneas del campo
    ctx.strokeStyle = 'rgba(255,255,255,0.7)';
    ctx.lineWidth = 1.5;
    const w = canvas.width, h = canvas.height;
    ctx.strokeRect(2, 2, w - 4, h - 4);          // Borde
    ctx.beginPath(); ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h); ctx.stroke(); // Línea central
    ctx.beginPath(); ctx.arc(w / 2, h / 2, h * 0.18, 0, Math.PI * 2); ctx.stroke(); // Círculo

    imgElement.src = canvas.toDataURL('image/png');
    const section = document.getElementById('spatial-heatmaps-section');
    if (section) section.style.display = 'block';
}

// Actualizar imágenes de heatmaps
let heatmapUpdateInterval = null;

function updateHeatmapImages() {
    if (!currentSessionId) {
        console.warn('No hay currentSessionId para actualizar heatmaps');
        return;
    }
    
    const timestamp = new Date().getTime();
    
    console.log('Actualizando heatmaps para session:', currentSessionId);
    
    const heatmapTeam0 = document.getElementById('heatmap-team-0');
    if (heatmapTeam0) {
        const url = `/api/heatmap/${currentSessionId}/0?t=${timestamp}`;
        console.log('Cargando heatmap Team 0:', url);
        heatmapTeam0.src = url;
    } else {
        console.error('No se encontró elemento heatmap-team-0');
    }
    
    const heatmapTeam1 = document.getElementById('heatmap-team-1');
    if (heatmapTeam1) {
        const url = `/api/heatmap/${currentSessionId}/1?t=${timestamp}`;
        console.log('Cargando heatmap Team 1:', url);
        heatmapTeam1.src = url;
    } else {
        console.error('No se encontró elemento heatmap-team-1');
    }
}

function updateFinalHeatmapImages() {
    if (!currentSessionId) {
        return;
    }

    const timestamp = new Date().getTime();
    const finalHeatmapTeam0 = document.getElementById('final-heatmap-team-0');
    const finalHeatmapTeam1 = document.getElementById('final-heatmap-team-1');

    if (finalHeatmapTeam0) {
        finalHeatmapTeam0.src = `/api/heatmap/${currentSessionId}/0?t=${timestamp}`;
    }
    if (finalHeatmapTeam1) {
        finalHeatmapTeam1.src = `/api/heatmap/${currentSessionId}/1?t=${timestamp}`;
    }
}

// Iniciar actualizaciones periódicas de heatmaps
function startHeatmapUpdates() {
    if (heatmapUpdateInterval) {
        clearInterval(heatmapUpdateInterval);
    }
    // Actualizar cada 3 segundos durante el análisis
    heatmapUpdateInterval = setInterval(updateHeatmapImages, 3000);
    console.log('Iniciado actualización periódica de heatmaps cada 3 segundos');
}

// Detener actualizaciones periódicas
function stopHeatmapUpdates() {
    if (heatmapUpdateInterval) {
        clearInterval(heatmapUpdateInterval);
        heatmapUpdateInterval = null;
        console.log('Detenidas actualizaciones periódicas de heatmaps');
    }
}

// Actualizar top zonas
function updateTopZones(teamId, zonePercentages) {
    if (!zonePercentages || !Array.isArray(zonePercentages)) return;

    // Crear array de zonas con índice y porcentaje
    const zones = zonePercentages.map((pct, idx) => ({
        index: idx,
        name: getTeamRelativeZoneLabelByIndex(idx, teamId, attackDirectionState),
        percent: Number(pct) || 0
    }));
    
    // Ordenar por porcentaje descendente
    zones.sort((a, b) => b.percent - a.percent);
    
    // Tomar top 3
    const top3 = zones.slice(0, 3);
    
    // Actualizar HTML
    const topZonesDiv = document.getElementById(`top-zones-team-${teamId}`);
    if (topZonesDiv) {
        const badgeClass = teamId === 0 ? 'bg-success' : 'bg-danger';
        topZonesDiv.innerHTML = top3.map((zone, i) =>
            `<span class="badge ${badgeClass} me-1">${i + 1}. ${zone.name} (${zone.percent.toFixed(1)}%)</span>`
        ).join('');
    }
}

function getTeamRelativeZoneLabelByIndex(zoneIndex, teamId, directionState) {
    // Partición thirds_lanes 3x3: indices [0..2]=tercio izq absoluto, [3..5]=centro, [6..8]=der.
    const yBand = ['Inferior', 'Medio', 'Superior'];
    if (!(zoneIndex >= 0 && zoneIndex < 9)) return `Zona ${zoneIndex}`;

    const col = Math.floor(zoneIndex / 3); // 0,1,2
    const band = yBand[zoneIndex % 3] || 'Medio';

    const attacksTo = teamId === 0
        ? directionState?.team_0_attacks_to
        : directionState?.team_1_attacks_to;

    // Si ataca a derecha: [0,1,2] => Defensa/Centro/Ataque
    // Si ataca a izquierda: invertido [0,1,2] => Ataque/Centro/Defensa
    let thirdsRight = ['Defensa', 'Centro', 'Ataque'];
    if (attacksTo === 'left') {
        thirdsRight = ['Ataque', 'Centro', 'Defensa'];
    } else if (attacksTo == null) {
        // Fallback conservador (mismo convenio que ataca a derecha)
        thirdsRight = ['Defensa', 'Centro', 'Ataque'];
    }
    const thirdName = thirdsRight[col] || 'Centro';
    return `${thirdName} - ${band}`;
}

function formatZoneName(zoneName) {
    if (!zoneName) return 'Zona desconocida';

    const zoneLabelMap = {
        def_left: 'Defensa - Inferior',
        def_center: 'Defensa - Medio',
        def_right: 'Defensa - Superior',
        mid_left: 'Centro - Inferior',
        mid_center: 'Centro - Medio',
        mid_right: 'Centro - Superior',
        off_left: 'Ataque - Inferior',
        off_center: 'Ataque - Medio',
        off_right: 'Ataque - Superior'
    };

    return zoneLabelMap[zoneName] || zoneName.replaceAll('_', ' ');
}

function normalizeZoneNamesInText(text) {
    if (!text || typeof text !== 'string') return text || '';
    const keys = [
        'def_left', 'def_center', 'def_right',
        'mid_left', 'mid_center', 'mid_right',
        'off_left', 'off_center', 'off_right'
    ];
    let output = text;
    for (const key of keys) {
        const label = formatZoneName(key);
        const regex = new RegExp(`\\b${key}\\b`, 'g');
        output = output.replace(regex, label);
    }
    return output;
}

function buildTwoLinePredictionMessage(alert) {
    const ep = alert?.data?.event_prediction || {};
    const eventTypeLabelMap = {
        dangerous_attack: 'ataque peligroso',
        shot: 'tiro',
        corner: 'córner',
        dangerous_transition: 'transición peligrosa',
        final_third_entry: 'entrada al último tercio',
        dangerous_turnover: 'pérdida peligrosa'
    };

    const teamLabel = (ep.team_id !== undefined && ep.team_id !== null) ? `Equipo ${ep.team_id}` : 'Equipo';
    const eventLabel = eventTypeLabelMap[ep.event_type] || ep.event_type || 'evento';
    const pct = ((Number(ep.probability) || 0) * 100).toFixed(0);
    const horizon = ep.time_horizon_sec ?? '-';

    const line1 = `Posible ${eventLabel} de ${teamLabel} (${pct}% en ~${horizon}s).`;

    const evidence = Array.isArray(ep.evidence) ? ep.evidence : [];
    const metrics = (ep.metrics && typeof ep.metrics === 'object') ? ep.metrics : {};
    const evidenceLabelMap = {
        defensive_resistance: 'la defensa rival está exigida',
        field_tilt: 'el juego está inclinado hacia campo rival',
        progression_rate: 'el equipo progresa con continuidad hacia portería',
        expected_threat_proxy: 'las acciones ofensivas tienen amenaza alta',
        box_entry_risk: 'hay llegadas frecuentes al área',
        final_third_presence: 'hay mucha presencia en último tercio',
        attacking_momentum: 'el ataque mantiene inercia positiva',
        wide_overload: 'se carga el ataque por bandas',
        offensive_pressure: 'la presión ofensiva es alta',
        shot_pressure_signal: 'se acumulan señales de finalización',
        transition_danger: 'hay riesgo de transición rápida',
        turnover_risk: 'hay riesgo de pérdida en zona sensible',
        final_third_entries_signal: 'se repiten entradas al último tercio',
        corner_likelihood_signal: 'el patrón de juego favorece córner'
    };

    const toNaturalEvidence = (raw) => {
        const txt = String(raw || '').replace('contexto_zonal:', '').trim();
        if (!txt) return '';
        const metricMatch = txt.match(/^([a-z_]+)=([0-9.]+)\*?([\-0-9.]*)$/i) || txt.match(/^([a-z_]+)=([0-9.]+)$/i);
        if (metricMatch) {
            const key = metricMatch[1];
            return evidenceLabelMap[key] || 'hay señales ofensivas favorables';
        }
        if (txt.startsWith('score_raw=')) return '';
        return txt;
    };

    const metricNum = (key) => {
        const v = Number(metrics[key]);
        return Number.isFinite(v) ? v : null;
    };

    const asPercentText = (value01) => `${Math.round(Math.max(0, Math.min(1, value01)) * 100)}%`;

    // Dato cuantificado en lenguaje natural (1 pista principal).
    const naturalQuantHints = [];
    const finalThirdPresence = metricNum('final_third_presence');
    if (finalThirdPresence !== null) {
        naturalQuantHints.push(`en los últimos segundos, ${asPercentText(finalThirdPresence)} de la posesión fue en zonas de ataque`);
    }
    const wideOverload = metricNum('wide_overload');
    if (wideOverload !== null) {
        naturalQuantHints.push(`aprox. ${asPercentText(wideOverload)} del juego ofensivo se cargó por bandas`);
    }
    const boxEntryRisk = metricNum('box_entry_risk');
    if (boxEntryRisk !== null) {
        naturalQuantHints.push(`la frecuencia de llegadas al área está en torno al ${asPercentText(boxEntryRisk)}`);
    }
    const transitionDanger = metricNum('transition_danger');
    if (transitionDanger !== null) {
        naturalQuantHints.push(`el riesgo de transición rápida está alrededor del ${asPercentText(transitionDanger)}`);
    }

    const keyEvidence = evidence
        .filter((e) => typeof e === 'string')
        .map((e) => toNaturalEvidence(e))
        .filter((e) => e.length > 0)
        .slice(0, 2);

    let line2 = 'Clave: presión ofensiva y contexto zonal.';
    const quantHint = naturalQuantHints[0] || '';
    if (keyEvidence.length > 0) {
        line2 = quantHint
            ? `Clave: ${keyEvidence.join('; ')}; ${quantHint}.`
            : `Clave: ${keyEvidence.join('; ')}.`;
    } else if (quantHint) {
        line2 = `Clave: ${quantHint}.`;
    }

    return `${line1}\n${line2}`;
}

// Función para mostrar el resumen de heatmaps
function showHeatmapSummary() {
    if (!currentSessionId) {
        console.error('No session ID available');
        return;
    }
    
    const summaryUrl = `/api/heatmap-summary/${currentSessionId}?t=${Date.now()}`;
    const summaryImg = document.getElementById('heatmap-summary-image');
    const downloadBtn = document.getElementById('download-summary-btn');
    
    // Actualizar imagen
    summaryImg.src = summaryUrl;
    
    // Actualizar botón de descarga
    downloadBtn.href = summaryUrl;
    
    // Mostrar modal
    const modal = new bootstrap.Modal(document.getElementById('heatmapSummaryModal'));
    modal.show();
}

// ====================
// Chatbot de Alertas Tácticas
// ====================

function handleAlert(alert) {
    console.log('Nueva alerta recibida:', alert);
    
    // Añadir a historial
    alertHistory.push(alert);
    
    // Mostrar el chatbot si está oculto
    const chatbot = document.getElementById('alert-chatbot');
    const toggleBtn = document.getElementById('chatbot-toggle-btn');
    
    if (chatbot.style.display === 'none') {
        chatbot.style.display = 'flex';
        toggleBtn.style.display = 'flex';
    }
    
    // Si el chatbot está minimizado, incrementar contador
    if (!chatbotOpen) {
        unreadAlerts++;
        updateChatbotBadge();
    }
    
    // Añadir mensaje al chatbot
    addAlertToChatbot(alert);
    
    // Auto-scroll al final
    const chatbotBody = document.getElementById('chatbot-messages');
    setTimeout(() => {
        chatbotBody.scrollTop = chatbotBody.scrollHeight;
    }, 100);
}

function addAlertToChatbot(alert) {
    const chatbotMessages = document.getElementById('chatbot-messages');
    
    // Mapear severidad a clase CSS
    const severityClass = alert.severity || 'info';
    
    // Mapear tipo a icono
    const iconMap = {
        'possession': 'fa-futbol',
        'passing': 'fa-shoe-prints',
        'zone': 'fa-map-marker-alt',
        'tactical': 'fa-chess',
        'prediction': 'fa-wand-magic-sparkles',
        'warning': 'fa-exclamation-triangle'
    };
    const icon = iconMap[alert.type] || 'fa-info-circle';
    
    // Formatear timestamp
    const date = new Date(alert.timestamp * 1000);
    const timeStr = date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    
    const relevanceScore = alert.data?.relevance_score;
    const predicted = alert.data?.predicted_events;
    let contextualHint = '';
    if (Array.isArray(alert.data?.dominant_zones) && alert.data.dominant_zones.length) {
        const topZones = alert.data.dominant_zones.slice(0, 2).map(formatZoneName).join(' y ');
        contextualHint = `\nFoco zonal: ${topZones}.`;
    } else if (Array.isArray(alert.data?.zones_affected) && alert.data.zones_affected.length) {
        const affected = alert.data.zones_affected.map(formatZoneName).join(', ');
        contextualHint = `\nZonas clave: ${affected}.`;
    }

    let predictionHint = '';
    if (alert.type === 'prediction' && alert.data?.event_prediction) {
        const ep = alert.data.event_prediction;
        const eventTypeLabelMap = {
            dangerous_attack: 'ataque peligroso',
            shot: 'tiro',
            corner: 'córner',
            dangerous_transition: 'transición peligrosa',
            final_third_entry: 'entrada a último tercio',
            dangerous_turnover: 'pérdida peligrosa'
        };
        const eventLabel = eventTypeLabelMap[ep.event_type] || ep.event_type || 'evento';
        const eventPct = ((Number(ep.probability) || 0) * 100).toFixed(1);
        predictionHint = `\nProbabilidad principal: ${eventLabel} ${eventPct}% en ${ep.time_horizon_sec ?? '-'}s.`;
    } else if (predicted && typeof predicted === 'object') {
        predictionHint = `\nProbabilidades: tiro ${predicted.shot ?? 0}%, gol ${predicted.goal ?? 0}%, córner ${predicted.corner ?? 0}%, falta peligrosa ${predicted.foul_in_danger_zone ?? 0}%.`;
    }

    const normalizedAlertMessage = normalizeZoneNamesInText(alert.message || '');
    const enrichedMessage = (alert.type === 'prediction' && alert.data?.event_prediction)
        ? buildTwoLinePredictionMessage(alert)
        : `${normalizedAlertMessage}${predictionHint}${contextualHint}`;
    const relevanceBadge = (typeof relevanceScore === 'number')
        ? `<span class="badge bg-dark-subtle text-dark ms-2">Relevancia ${(relevanceScore * 100).toFixed(0)}%</span>`
        : '';

    // Crear elemento de alerta
    const alertElement = document.createElement('div');
    alertElement.className = `alert-message ${severityClass}`;
    alertElement.innerHTML = `
        <div class="alert-icon">
            <i class="fas ${icon}"></i>
        </div>
        <div class="alert-content">
            <div class="alert-title">${alert.title}${relevanceBadge}</div>
            <div class="alert-text">${enrichedMessage}</div>
            <div class="alert-timestamp">
                <i class="fas fa-clock"></i> ${timeStr} | Frame ${alert.frame_id}
            </div>
        </div>
    `;
    
    chatbotMessages.appendChild(alertElement);
    
    // Limitar a 50 alertas en el DOM (performance)
    const messages = chatbotMessages.querySelectorAll('.alert-message:not(.welcome-message .alert-message)');
    if (messages.length > 50) {
        messages[0].remove();
    }
}

function toggleChatbot() {
    const chatbot = document.getElementById('alert-chatbot');
    const toggleBtn = document.getElementById('chatbot-toggle-btn');
    
    if (chatbotOpen) {
        // Minimizar
        chatbot.style.display = 'none';
        toggleBtn.style.display = 'flex';
        chatbotOpen = false;
    } else {
        // Abrir
        chatbot.style.display = 'flex';
        toggleBtn.style.display = 'none';
        chatbotOpen = true;
        
        // Resetear contador de no leídas
        unreadAlerts = 0;
        updateChatbotBadge();
    }
}

function updateChatbotBadge() {
    const badge = document.getElementById('chatbot-badge');
    if (unreadAlerts > 0) {
        badge.textContent = unreadAlerts;
        badge.style.display = 'block';
    } else {
        badge.style.display = 'none';
    }
}

function clearAlerts() {
    if (confirm('¿Estás seguro de que quieres borrar todas las alertas?')) {
        const chatbotMessages = document.getElementById('chatbot-messages');
        // Mantener solo el mensaje de bienvenida
        const welcomeMsg = chatbotMessages.querySelector('.welcome-message');
        chatbotMessages.innerHTML = '';
        if (welcomeMsg) {
            chatbotMessages.appendChild(welcomeMsg);
        }
        alertHistory = [];
        unreadAlerts = 0;
        updateChatbotBadge();
    }
}

// Iniciar chatbot cuando comienza el análisis
function initializeChatbot() {
    const chatbot = document.getElementById('alert-chatbot');
    const toggleBtn = document.getElementById('chatbot-toggle-btn');
    
    // Mostrar el chatbot al inicio
    chatbot.style.display = 'flex';
    toggleBtn.style.display = 'none';
    chatbotOpen = true;
    
    // Resetear estado
    alertHistory = [];
    unreadAlerts = 0;
    updateChatbotBadge();
    
    // Limpiar mensajes anteriores (mantener welcome)
    const chatbotMessages = document.getElementById('chatbot-messages');
    const welcomeMsg = chatbotMessages.querySelector('.welcome-message');
    chatbotMessages.innerHTML = '';
    if (welcomeMsg) {
        chatbotMessages.appendChild(welcomeMsg);
    }
}
