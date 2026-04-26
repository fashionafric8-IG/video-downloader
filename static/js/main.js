const analyzeBtn = document.getElementById('analyze-btn');
const urlInput = document.getElementById('url-input');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const errorMsg = document.getElementById('error-msg');
const results = document.getElementById('results');
const formatsList = document.getElementById('formats-list');
const downloadOverlay = document.getElementById('download-overlay');
const finalDownloadBtn = document.getElementById('final-download-btn');
const overlayTitle = document.getElementById('overlay-title');
const overlayMsg = document.getElementById('overlay-msg');
const downloadLoader = document.getElementById('download-loader');
const downloadSuccess = document.getElementById('download-success');

async function pasteFromClipboard() {
    try {
        const text = await navigator.clipboard.readText();
        urlInput.value = text;
        urlInput.focus();
    } catch (err) {
        console.error('Failed to read clipboard:', err);
    }
}

analyzeBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) return;

    resetUI();
    loading.classList.remove('hidden');

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        const data = await response.json();
        if (data.error) throw new Error(data.error);

        renderResults(data, url);
    } catch (err) {
        showError(err.message);
    } finally {
        loading.classList.add('hidden');
    }
});

function renderResults(data, originalUrl) {
    document.getElementById('title').textContent = data.title;
    document.getElementById('thumb').src = data.thumbnail;
    document.getElementById('duration').textContent = data.duration || 'Unknown Duration';
    
    formatsList.innerHTML = '';
    
    // Show top 6 quality formats
    const displayFormats = data.formats.slice(0, 6);
    
    displayFormats.forEach(f => {
        const row = document.createElement('div');
        row.className = 'glass-card rounded-2xl p-5 flex items-center justify-between hover:bg-white/5 transition-all group cursor-pointer';
        
        const badgeColor = f.combined ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20' : 'bg-slate-500/10 text-slate-400 border-white/5';
        const badgeText = f.combined ? 'Recommended' : 'Standard';

        row.innerHTML = `
            <div class="flex items-center gap-5">
                <div class="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center text-xl text-indigo-400 group-hover:scale-110 transition-transform">
                    <i class="fas ${f.type === 'Video' ? 'fa-video' : 'fa-music'}"></i>
                </div>
                <div>
                    <div class="flex items-center gap-3 mb-1">
                        <span class="text-lg font-bold text-white">${f.res}</span>
                        <span class="text-[10px] px-2 py-0.5 rounded-md border font-bold uppercase tracking-widest ${badgeColor}">${badgeText}</span>
                    </div>
                    <div class="flex items-center gap-3 text-xs text-slate-500 font-medium">
                        <span class="uppercase tracking-widest">${f.ext}</span>
                        <div class="w-1 h-1 rounded-full bg-slate-700"></div>
                        <span>${f.size}</span>
                        <div class="w-1 h-1 rounded-full bg-slate-700"></div>
                        <span class="text-slate-400">${f.type}</span>
                    </div>
                </div>
            </div>
            <button onclick="triggerDownload('${originalUrl}', '${f.id}')" 
                    class="bg-white/5 hover:bg-indigo-600 text-white w-12 h-12 rounded-xl transition-all flex items-center justify-center shadow-lg group-hover:shadow-indigo-500/20 group-hover:border-indigo-500/50 border border-white/10">
                <i class="fas fa-arrow-down"></i>
            </button>
        `;
        formatsList.appendChild(row);
    });

    results.classList.remove('hidden');
    results.scrollIntoView({ behavior: 'smooth' });
}

async function triggerDownload(url, formatId) {
    downloadOverlay.classList.remove('hidden');
    overlayTitle.textContent = "Optimizing File";
    overlayMsg.textContent = "Processing the high-quality stream for local playback...";
    downloadLoader.classList.remove('hidden');
    downloadSuccess.classList.add('hidden');
    finalDownloadBtn.classList.add('hidden');

    try {
        const response = await fetch('/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, format_id: formatId })
        });

        const data = await response.json();
        if (data.error) throw new Error(data.error);

        // Success state
        downloadLoader.classList.add('hidden');
        downloadSuccess.classList.remove('hidden');
        overlayTitle.textContent = "Ready";
        overlayMsg.textContent = "Processing complete. Click below to save the playable file to your computer.";
        finalDownloadBtn.textContent = "Download";
        
        finalDownloadBtn.href = `/serve/${encodeURIComponent(data.filename)}`;
        finalDownloadBtn.classList.remove('hidden');
    } catch (err) {
        overlayTitle.textContent = "Process Failed";
        overlayMsg.textContent = err.message;
        downloadLoader.classList.add('hidden');
    }
}

function closeOverlay() {
    downloadOverlay.classList.add('hidden');
}

function resetUI() {
    results.classList.add('hidden');
    error.classList.add('hidden');
}

function showError(msg) {
    error.classList.remove('hidden');
    errorMsg.textContent = msg;
}
