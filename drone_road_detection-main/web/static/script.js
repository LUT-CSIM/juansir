/*
 * JavaScript for the EdgeAI dashboard. This script initialises charts and
 * loads batch-specific data for the video and defect list.
 */

document.addEventListener('DOMContentLoaded', () => {
    const defectContainer = document.querySelector('.defect-track-container');
    const batchDefectCount = document.getElementById('batchDefectCount');
    const batchPendingCount = document.getElementById('batchPendingCount');
    const batchCompletionRate = document.getElementById('batchCompletionRate');

    let isDown = false;
    let startX, scrollLeft;

    defectContainer.addEventListener('mousedown', (e) => {
        isDown = true;
        defectContainer.classList.add('grabbing');
        startX = e.pageX - defectContainer.offsetLeft;
        scrollLeft = defectContainer.scrollLeft;
    });

    defectContainer.addEventListener('mouseleave', () => {
        isDown = false;
        defectContainer.classList.remove('grabbing');
    });

    defectContainer.addEventListener('mouseup', () => {
        isDown = false;
        defectContainer.classList.remove('grabbing');
    });

    defectContainer.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - defectContainer.offsetLeft;
        const walk = (x - startX) * 1.5;
        defectContainer.scrollLeft = scrollLeft - walk;
    });

    // Load dashboard statistics
    fetch('/api/stats/')
        .then(resp => resp.json())
        .then(data => {
            document.getElementById('inspectionCount').textContent = data.inspection_count;
            document.getElementById('pendingCount').textContent = data.pending_count;
            document.getElementById('completionRate').textContent = data.completion_rate + '%';
        });

    // Load road overview numbers
    fetch('/api/road_stats/')
        .then(resp => resp.json())
        .then(data => {
            document.getElementById('roadMileage').textContent = data.total_length;
            document.getElementById('roadCount').textContent = data.total_count;
        });

    // Load today's weather information
    fetch('/api/weather/')
        .then(resp => resp.json())
        .then(data => {
            document.getElementById('weatherText').textContent = data.weather;
            document.getElementById('temperatureText').textContent = data.temperature + '℃';
            const icon = document.querySelector('#weatherWidget .weather-icon');
            if (data.code) {
                icon.classList.add(data.code);
            }
        });

    // Load disease type distribution for donut chart
    fetch('/api/disease_types/')
        .then(resp => resp.json())
        .then(data => {
            const leftCtx = document.getElementById('leftDonutChart').getContext('2d');
            const baseColors = ['#00c0ff', '#0078b3', '#005c8d', '#164a8a', '#092f55'];
            const colors = [];
            for (let i = 0; i < data.labels.length; i++) {
                colors.push(baseColors[i % baseColors.length]);
            }
            new Chart(leftCtx, {
                type: 'doughnut',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.data,
                        backgroundColor: colors,
                        hoverOffset: 4,
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#e5efff',
                                font: {
                                    size: 10
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: (context) => `${context.label}: ${context.parsed}`
                            }
                        }
                    }
                }
            });
        });

    // Initialise the right line chart
    const rightCtx = document.getElementById('rightLineChart').getContext('2d');
    new Chart(rightCtx, {
        type: 'line',
        data: {
            labels: ['9.1', '9.2', '9.3', '9.4', '9.5', '9.6', '9.7'],
            datasets: [{
                label: '巡检里程 (km)',
                data: [500, 420, 600, 550, 700, 450, 480],
                borderColor: '#00c0ff',
                backgroundColor: 'rgba(0, 192, 255, 0.2)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    ticks: {
                        color: '#7fa3c9'
                    },
                    grid: {
                        color: 'rgba(255,255,255,0.05)'
                    }
                },
                y: {
                    ticks: {
                        color: '#7fa3c9'
                    },
                    grid: {
                        color: 'rgba(255,255,255,0.05)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.parsed.y} km`
                    }
                }
            }
        }
    });

    // Draw detection boxes on the video
    const video = document.getElementById('detectionVideo');
    const overlay = document.querySelector('.video-overlay');
    const canvas = document.createElement('canvas');
    overlay.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    const replayBtn = document.getElementById('replayButton');

    let frameMap = new Map();

    function loadBatch(batchId) {
        frameMap = new Map();
        fetch(`/api/boxes/?batch=${batchId}`)
            .then(resp => resp.json())
            .then(data => {
                data.frames.forEach(f => {
                    frameMap.set(Math.round(f.time * 1000), f.boxes);
                });
                if (data.video) {
                    video.src = data.video;
                    video.load();
                    video.play().catch(() => {});
                }
            });

        fetch(`/api/tracks/?batch=${batchId}`)
            .then(resp => resp.json())
            .then(data => {
                const container = defectContainer;
                container.innerHTML = '';
                data.tracks.forEach(t => {
                    const item = document.createElement('div');
                    item.className = 'track-item';
                    const img = document.createElement('img');
                    img.src = t.snapshot;
                    item.appendChild(img);
                    const caption = document.createElement('span');
                    const severityText = t.severity ? ` - ${t.severity}` : '';
                    caption.textContent = `${t.label}${severityText}`;
                    item.appendChild(caption);
                    item.addEventListener('click', () => {
                        video.currentTime = t.start;
                        // Hide replay button if visible and resume playback
                        replayBtn.classList.remove('show');
                        video.play();
                    });
                    container.appendChild(item);
                });
            });

        fetch(`/api/stats/?batch=${batchId}`)
            .then(resp => resp.json())
            .then(data => {
                if (data.batch) {
                    batchDefectCount.textContent = data.batch.defect_count;
                    batchPendingCount.textContent = data.batch.pending_count;
                    batchCompletionRate.textContent = data.batch.completion_rate + '%';
                }
            });
    }

    const colorMap = {
        '裂缝': '#ff0000',
        '坑槽': '#00ff00',
        '松散': '#0000ff',
        '沉陷': '#ffff00'
    };

    function drawBoxes(context, w, h, boxes) {
        context.lineWidth = 2;
        context.font = '16px sans-serif';
        boxes.forEach(b => {
            const color = colorMap[b.label] || '#00ff00';
            context.strokeStyle = color;
            context.fillStyle = color;
            context.strokeRect(b.x * w, b.y * h, b.w * w, b.h * h);
            context.fillText(b.label, b.x * w, b.y * h - 4);
        });
    }

    function adjustCanvasSize() {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.style.width = video.clientWidth + 'px';
        canvas.style.height = video.clientHeight + 'px';
    }

    video.addEventListener('loadedmetadata', adjustCanvasSize);
    window.addEventListener('resize', adjustCanvasSize);

    function drawFrameAt(time) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const boxes = frameMap.get(Math.round(time * 1000));
        if (boxes) {
            drawBoxes(ctx, canvas.width, canvas.height, boxes);
        }
    }

    function rafRender() {
        drawFrameAt(video.currentTime);
        if (!video.paused && !video.ended) {
            requestAnimationFrame(rafRender);
        }
    }

    function vfcRender(_now, metadata) {
        drawFrameAt(metadata.mediaTime);
        if (!video.paused && !video.ended) {
            video.requestVideoFrameCallback(vfcRender);
        }
    }

    video.addEventListener('play', () => {
        // Ensure replay button is hidden whenever playback starts
        replayBtn.classList.remove('show');
        if (video.requestVideoFrameCallback) {
            video.requestVideoFrameCallback(vfcRender);
        } else {
            requestAnimationFrame(rafRender);
        }
    });

    video.addEventListener('pause', () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    });

    video.addEventListener('ended', () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        replayBtn.classList.add('show');
    });

    replayBtn.addEventListener('click', () => {
        replayBtn.classList.remove('show');
        video.currentTime = 0;
        video.play();
    });

    // Load detection batch list and initialise
    fetch('/api/batches/')
        .then(resp => resp.json())
        .then(data => {
            const list = document.getElementById('batchList');
            list.innerHTML = '';
            data.batches.forEach((b, idx) => {
                const li = document.createElement('li');
                li.innerHTML = `<span class="rank">${idx + 1}.</span> ${b.name}`;
                li.addEventListener('click', () => loadBatch(b.id));
                list.appendChild(li);
            });
            if (data.batches.length) {
                loadBatch(data.batches[0].id);
            }
        });
});
