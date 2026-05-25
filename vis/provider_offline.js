// ==========================================
// provider_offline.js
// OFFLINE FILE PARSER & PLAYBACK CONTROLLER
// ==========================================

const OfflineProvider = {
    parsedData: null,
    uploadedFilePointer: null,
    currentLoadedChunkIndex: -1,
    headerLengthOffset: 0,
    chunkLoadPromise: null,
    chunkLoadIndexInFlight: -1,

    currentTime: 0, minTime: 0, maxTime: 0, timeMultiplier: 1,
    isPlaying: false, animationFrameId: null, lastFrameTime: 0, lastDynUpdate: 0,

    init: function() {
        document.getElementById("profileLoader")?.addEventListener("change", (e) => this.handleFileUpload(e));
        document.getElementById("btn-play")?.addEventListener("click", () => this.togglePlayback());
        document.getElementById("timeSlider")?.addEventListener("input", (e) => { document.getElementById("currentTimeLabel").textContent = parseFloat(e.target.value).toFixed(3); });
        document.getElementById("timeSlider")?.addEventListener("change", (e) => { this.pausePlayback(); this.seekToTime(parseFloat(e.target.value)); });
        document.getElementById("speedSlider")?.addEventListener("input", (e) => { document.getElementById("speedLabel").textContent = Math.pow(10, parseFloat(e.target.value)).toFixed(3) + "x"; });
        
        VisualiserCore.init("visCanvas");
    },

    decompressBlob: async function(blob) {
        const ds = new DecompressionStream('deflate');
        return await new Response(blob.stream().pipeThrough(ds)).text();
    },

    handleFileUpload: async function(event) {
        this.uploadedFilePointer = event.target.files[0];
        if (!this.uploadedFilePointer) return;

        try {
            const sizeBuf = await this.uploadedFilePointer.slice(0, 4).arrayBuffer();
            this.headerLengthOffset = 4 + new DataView(sizeBuf).getUint32(0, true);
            const headerText = await this.decompressBlob(this.uploadedFilePointer.slice(4, this.headerLengthOffset));
            
            this.parsedData = JSON.parse(headerText);
            
            window.parsedData = this.parsedData; 
            
            this.parsedData.timeline = [];
            this.currentLoadedChunkIndex = -1;
            
            this.initDashboard();
        } catch (error) {
            alert("Failed to parse the MPI profile data.");
            console.error(error);
        }
    }, 

    ensureValidTopology: function() {
	const metadata = this.parsedData.metadata || this.parsedData.info || {};

	if (!Array.isArray(this.parsedData.topology)) {
            this.parsedData.topology = [];
	}

	const topology = this.parsedData.topology;
	const totalRanks = Number(metadata.total_ranks || topology.length || 0);

	// If topology is completely missing, create a realistic fallback
	// This topology isn't the system map that can be provided, this is the 
	// information for the individual processes that should be collected at runtime.
	// Really we should fix this in the parser rather than faking it here.
	// TODO: Move to the parser.
        
	if (topology.length === 0) {
            for (let i = 0; i < totalRanks; i++) {
		topology.push({
                    rank: i,
                    hostname: "node-0",
                    chip: 0,
                    core: i
		});
            }
	}

	const hosts = new Map();

	// --------------------------------------------------
	// Group by hostname, then by raw chip
	// --------------------------------------------------
	topology.forEach((rankObj, idx) => {
            if (!Number.isFinite(rankObj.rank)) {
		rankObj.rank = idx;
            }

            let host = (typeof rankObj.hostname === "string") ? rankObj.hostname.trim() : "";
            if (!host) host = "node-0";
            rankObj.hostname = host;

            const rawChip = Number.isFinite(rankObj.chip) ? rankObj.chip : 0;
            const rawCore = Number.isFinite(rankObj.core) ? rankObj.core : rankObj.rank;

            // Preserve original values for debugging/reference
            rankObj.raw_chip = rawChip;
            rankObj.raw_core = rawCore;

            if (!hosts.has(host)) {
		hosts.set(host, {
                    hostName: host,
                    ranks: [],
                    chipGroups: new Map(),
                    inferredCpuCount: 1,
                    inferredCoresPerCpu: 1
		});
            }

            const h = hosts.get(host);
            h.ranks.push(rankObj);

            if (!h.chipGroups.has(rawChip)) {
		h.chipGroups.set(rawChip, []);
            }
            h.chipGroups.get(rawChip).push(rankObj);
	});

	const hostList = Array.from(hosts.values()).sort((a, b) =>
							 a.hostName.localeCompare(b.hostName, undefined, { numeric: true, sensitivity: "base" })
							);

	// --------------------------------------------------
	// For each host, infer a dense visual topology
	//
	//    - visual chip IDs become 0..N-1
	//    - visual core IDs become 0..K-1 within each chip
	//
	// This avoids sparse/global raw IDs turning into
	// 128-core processors, 9 chips, etc.
	// --------------------------------------------------
	hostList.forEach((hostObj) => {
            const chipEntries = Array.from(hostObj.chipGroups.entries()).sort((a, b) => {
		const aChip = Number.isFinite(a[0]) ? a[0] : 0;
		const bChip = Number.isFinite(b[0]) ? b[0] : 0;
		return aChip - bChip;
            });

            let maxRanksOnAnyChip = 0;

            chipEntries.forEach(([rawChip, chipRanks], visualChipIdx) => {
		// Sort deterministically by raw core, then rank
		chipRanks.sort((a, b) => {
                    const ac = Number.isFinite(a.raw_core) ? a.raw_core : a.rank;
                    const bc = Number.isFinite(b.raw_core) ? b.raw_core : b.rank;
                    if (ac !== bc) return ac - bc;
                    return a.rank - b.rank;
		});

		// Dense remap within this chip.
		// Even if raw cores are global/sparse/non-contiguous, the display stays sensible.
		chipRanks.forEach((rankObj, visualCoreIdx) => {
                    rankObj.chip = visualChipIdx;
                    rankObj.core = visualCoreIdx;
		});

		if (chipRanks.length > maxRanksOnAnyChip) {
                    maxRanksOnAnyChip = chipRanks.length;
		}
            });

            hostObj.inferredCpuCount = Math.max(1, chipEntries.length);
            hostObj.inferredCoresPerCpu = Math.max(1, maxRanksOnAnyChip);
	});

	// --------------------------------------------------
	// Build/update a flat blueprint that
	// VisualiserCore.buildTopology() understands
	// --------------------------------------------------
	const existingBp = this.parsedData.hardware_blueprint;
	const existingFlatBlueprint =
            existingBp &&
            typeof existingBp === "object" &&
            !Array.isArray(existingBp) &&
            !Array.isArray(existingBp.cabinets);

	const cols = Math.ceil(Math.sqrt(hostList.length || 1));
	const rows = Math.ceil((hostList.length || 1) / cols);
	const hostSpacing = 18;

	const flatBlueprint = {
            metadata: {
		system_name: metadata.system_name || "Inferred Process Topology"
            }
	};

	hostList.forEach((hostObj, index) => {
            const col = index % cols;
            const row = Math.floor(index / cols);

            const existingHostEntry = existingFlatBlueprint ? existingBp[hostObj.hostName] : null;

            flatBlueprint[hostObj.hostName] = {
		x: Number.isFinite(existingHostEntry?.x)
                    ? existingHostEntry.x
                    : (col - (cols - 1) / 2) * hostSpacing,
		y: Number.isFinite(existingHostEntry?.y)
                    ? existingHostEntry.y
                    : 0,
		z: Number.isFinite(existingHostEntry?.z)
                    ? existingHostEntry.z
                    : (row - (rows - 1) / 2) * hostSpacing,
		cpus: hostObj.inferredCpuCount,
		cores_per_cpu: hostObj.inferredCoresPerCpu
            };
	});

	this.parsedData.hardware_blueprint = flatBlueprint;

	console.log("Inferred topology:");
	hostList.forEach(h => {
            console.log(
		h.hostName,
		`chips=${h.inferredCpuCount}`,
		`max-ranks-per-chip=${h.inferredCoresPerCpu}`,
		Array.from(h.chipGroups.entries()).map(([chip, ranks]) => ({
                    rawChip: chip,
                    ranks: ranks.length
		}))
            );
	});
    },

    initDashboard: function() {
        this.pausePlayback();
        VisualiserCore.clearTopology();

        const chunks = this.parsedData.chunks;
        this.minTime = (chunks && chunks.length > 0) ? chunks[0].t_start : 0;
        this.maxTime = (chunks && chunks.length > 0) ? chunks[chunks.length - 1].t_end : 0;
        this.timeMultiplier = (this.maxTime - this.minTime > 0) ? (this.maxTime - this.minTime) / 10.0 : 1;

        const slider = document.getElementById("timeSlider");
        if (slider) { slider.step = "any"; slider.min = this.minTime; slider.max = this.maxTime; slider.disabled = false; }
        if (document.getElementById("btn-play")) document.getElementById("btn-play").disabled = false;

	this.ensureValidTopology();

        // Hand the blueprint off to the core
        VisualiserCore.buildTopology(this.parsedData.hardware_blueprint, this.parsedData.topology, this.parsedData.metadata || this.parsedData.info);
        VisualiserCore.initSpectrograms(this.parsedData.statistics);

        if (window.AnalyticsUI) {
            AnalyticsUI.renderAnalytics(window.parsedData);
        }
        if (window.Analytics3D) {
            Analytics3D.setAnalysis(window.parsedData.analysis);
            Analytics3D.refreshHighlights();
        }

        this.seekToTime(this.minTime).catch(err => { console.error(err); this.pausePlayback(); });
    },

    ensureChunkLoadedForTime: async function(time) {
        if (!this.parsedData?.chunks || !this.uploadedFilePointer) return;
        const chunks = this.parsedData.chunks;

        while (true) {
            let targetIndex = chunks.findIndex(c => time <= c.t_end);
            if (targetIndex === -1) targetIndex = chunks.length - 1;

            const requiredKey = `${Math.max(0, targetIndex - 1)}:${targetIndex}`;
            if (this.currentLoadedChunkIndex === requiredKey) return;

            if (this.chunkLoadPromise) {
                if (this.chunkLoadIndexInFlight === requiredKey) {
                    await this.chunkLoadPromise;
                    return;
                }
                await this.chunkLoadPromise;
                continue;
            }

            this.chunkLoadIndexInFlight = requiredKey;
            const overlay = document.getElementById("loadingOverlay");
            const loadingText = document.getElementById("loadingText");

            this.chunkLoadPromise = (async () => {
                try {
                    if (overlay) overlay.style.display = "block";
                    if (loadingText) loadingText.textContent = `Unpacking Chunk ${targetIndex + 1}...`;
                    await new Promise(r => setTimeout(r, 0));

                    const indices = [];
                    if (targetIndex > 0) indices.push(targetIndex - 1);
                    indices.push(targetIndex);

                    let mergedTimeline = [];

                    for (const idx of indices) {
                        const c = chunks[idx];
                        const blob = this.uploadedFilePointer.slice(
                            this.headerLengthOffset + c.offset,
                            this.headerLengthOffset + c.offset + c.size
                        );
                        const chunkTimeline = JSON.parse(await this.decompressBlob(blob));
                        mergedTimeline = mergedTimeline.concat(chunkTimeline);
                    }

                    if (mergedTimeline.length > 1) {
                        mergedTimeline.sort((a, b) => a.time - b.time);
                    }

                    this.parsedData.timeline = mergedTimeline;
                    this.currentLoadedChunkIndex = requiredKey;
                } finally {
                    if (overlay) overlay.style.display = "none";
                }
            })();

            await this.chunkLoadPromise;
            this.chunkLoadPromise = null;
            this.chunkLoadIndexInFlight = -1;
            return;
        }
    },

    seekToTime: async function(time) {
        this.currentTime = time;
        if (document.getElementById("timeSlider")) document.getElementById("timeSlider").value = this.currentTime;
        if (document.getElementById("currentTimeLabel")) document.getElementById("currentTimeLabel").textContent = this.currentTime.toFixed(3);
        
        if (window.AnalyticsUI) {
            AnalyticsUI.updateAnalyticsTimeWindowIndicator(this.currentTime);
        }
        
        await this.ensureChunkLoadedForTime(this.currentTime);
        const activeEvents = this.getActiveEventsForWindow();
	
        VisualiserCore.clearGlow();
	
        VisualiserCore.renderFrame(activeEvents);
        VisualiserCore.updateDynamicSpectrogram(activeEvents, this.parsedData.statistics);
    },

    getActiveEventsForWindow: function() {
        const raw = parseFloat(document.getElementById("speedSlider")?.value || "0");
        const winSize = Math.min(0.2, 0.05 * Math.pow(10, raw));
        const minWin = this.currentTime - winSize;
        const minCollWin = this.currentTime - Math.max(winSize * 8.0, 0.5);

        const timeline = this.parsedData.timeline;
        const activeEvents = [];
        if (!timeline || timeline.length === 0) return activeEvents;

        let l = 0, r = timeline.length - 1, m = 0;
        while (l <= r) {
            m = Math.floor((l + r) / 2);
            if (timeline[m].time <= this.currentTime) l = m + 1;
            else r = m - 1;
        }

        let captured = 0;
        for (let i = r; i >= 0; i--) {
            const ev = timeline[i];
            const evTime = ev.time;
            const callType = ev.call || ev.message_type;
            const cat = window.VisualiserCore ? window.VisualiserCore.MPI_CATEGORIES[callType] : null || { type: "unknown" };
            const isColl = (cat.type === "collective" || cat.type === "lifecycle");

            if (evTime >= minCollWin) {
                if (evTime >= minWin || isColl) {
                    activeEvents.push(ev);
                    if (++captured >= 800) break;
                }
            } else {
                break;
            }
        }

        return activeEvents.reverse();
    },

    togglePlayback: function() {
        this.isPlaying = !this.isPlaying;
        VisualiserCore.isDecayEnabled = this.isPlaying;
        const btn = document.getElementById("btn-play");
        if (btn) btn.innerHTML = this.isPlaying ? "<b>|| Pause</b>" : "<b>▶ Play</b>";
        if (this.isPlaying) { this.lastFrameTime = performance.now(); this.playLoop(performance.now()); }
        else cancelAnimationFrame(this.animationFrameId);
    },

    pausePlayback: function() {
        this.isPlaying = false;
        VisualiserCore.isDecayEnabled = false;
        const btn = document.getElementById("btn-play");
        if (btn) btn.innerHTML = "<b>▶ Play</b>";
        cancelAnimationFrame(this.animationFrameId);
    },

    playLoop: async function(timestamp) {
        if (!this.isPlaying) return;
        const dt = Math.min((timestamp - this.lastFrameTime) / 1000, 0.05);
        this.lastFrameTime = timestamp;
        
        const speed = Math.pow(10, parseFloat(document.getElementById("speedSlider")?.value || "0"));
        let nextTime = this.currentTime + (dt * this.timeMultiplier * speed);

        if (nextTime >= this.maxTime) { await this.seekToTime(this.maxTime); this.pausePlayback(); return; }

        this.currentTime = nextTime;
        if (document.getElementById("timeSlider")) document.getElementById("timeSlider").value = this.currentTime;
        if (document.getElementById("currentTimeLabel")) document.getElementById("currentTimeLabel").textContent = this.currentTime.toFixed(3);

        if (window.AnalyticsUI) {
            AnalyticsUI.updateAnalyticsTimeWindowIndicator(this.currentTime);
        }

        await this.ensureChunkLoadedForTime(this.currentTime);
        const activeEvents = this.getActiveEventsForWindow();
        
        VisualiserCore.renderFrame(activeEvents);
        if (timestamp - this.lastDynUpdate > 100) { VisualiserCore.updateDynamicSpectrogram(activeEvents, this.parsedData.statistics); this.lastDynUpdate = timestamp; }

        if (this.isPlaying) this.animationFrameId = requestAnimationFrame((ts) => this.playLoop(ts));
    }
};

document.addEventListener("DOMContentLoaded", () => OfflineProvider.init());
