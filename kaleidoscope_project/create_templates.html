#!/bin/bash

# Create templates directory
mkdir -p templates
mkdir -p static/css
mkdir -p static/js

# Create index.html template
cat > templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kaleidoscope AI</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">Kaleidoscope AI</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link active" href="/">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/settings">Settings</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    
    <div class="container mt-4">
        <div class="row">
            <div class="col-lg-12">
                <div class="card mb-4">
                    <div class="card-header bg-primary text-white">
                        <h4>Software Ingestion</h4>
                    </div>
                    <div class="card-body">
                        <form id="upload-form" enctype="multipart/form-data">
                            <div class="mb-3">
                                <label for="file" class="form-label">Select software file to ingest</label>
                                <input class="form-control" type="file" id="file" name="file">
                                <div class="form-text">Supported file types: binaries (exe, dll, so), source code (py, js, c, cpp, java)</div>
                            </div>
                            <button type="submit" class="btn btn-primary">Upload & Analyze</button>
                        </form>
                        <div id="upload-progress" class="mt-3 d-none">
                            <div class="alert alert-processing">
                                <div class="d-flex align-items-center">
                                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                                    <span>Processing... This may take some time.</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div id="task-section" class="d-none">
                    <div class="card mb-4">
                        <div class="card-header bg-info text-white">
                            <h4>Current Task</h4>
                        </div>
                        <div class="card-body">
                            <div id="current-task-info"></div>
                        </div>
                    </div>
                </div>
                
                <div id="mimic-section" class="d-none">
                    <div class="card mb-4">
                        <div class="card-header bg-success text-white">
                            <h4>Generate Mimicked Software</h4>
                        </div>
                        <div class="card-body">
                            <form id="mimic-form">
                                <input type="hidden" id="source-task-id" name="source-task-id">
                                <div class="mb-3">
                                    <label for="target-language" class="form-label">Target Language</label>
                                    <select class="form-select" id="target-language" name="target-language">
                                        <option value="python">Python</option>
                                        <option value="javascript">JavaScript</option>
                                        <option value="cpp">C++</option>
                                    </select>
                                </div>
                                <button type="submit" class="btn btn-success">Generate Mimicked Software</button>
                            </form>
                        </div>
                    </div>
                </div>
                
                <div id="result-section" class="d-none">
                    <div class="card mb-4">
                        <div class="card-header bg-success text-white">
                            <h4>Results</h4>
                        </div>
                        <div class="card-body">
                            <div id="result-content"></div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header bg-secondary text-white">
                        <h4>Task History</h4>
                    </div>
                    <div class="card-body">
                        <div id="task-history" class="list-group"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/static/js/main.js"></script>
</body>
</html>
EOF

# Create settings.html template
cat > templates/settings.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Settings - Kaleidoscope AI</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="/">Kaleidoscope AI</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Home</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/settings">Settings</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    
    <div class="container mt-4">
        <h1>Kaleidoscope AI Settings</h1>
        
        {% if message %}
        <div class="alert alert-success">
            {{ message }}
        </div>
        {% endif %}
        
        {% if error %}
        <div class="alert alert-danger">
            Error: {{ error }}
        </div>
        {% endif %}
        
        <div class="card mt-4">
            <div class="card-header bg-primary text-white">
                <h4>Ollama Model Settings</h4>
            </div>
            <div class="card-body">
                <form method="post">
                    <div class="mb-3">
                        <label for="default_model" class="form-label">Default Model</label>
                        <select class="form-select" id="default_model" name="default_model">
                            {% for model in available_models %}
                            <option value="{{ model }}" {% if config.ollama_settings.default_model == model %}selected{% endif %}>{{ model }}</option>
                            {% endfor %}
                        </select>
                        <div class="form-text">The model used for generating specifications and code.</div>
                    </div>
                    <div class="mb-3">
                        <label for="temperature" class="form-label">Temperature</label>
                        <input type="range" class="form-range" min="0" max="1" step="0.1" id="temperature" name="temperature" value="{{ config.ollama_settings.temperature }}">
                        <div class="form-text">Current value: <span id="temperature-value">{{ config.ollama_settings.temperature }}</span></div>
                        <div class="form-text">Lower values (0.0-0.3) for more deterministic outputs, higher values for more creative outputs.</div>
                    </div>
                    <div class="mb-3">
                        <label for="max_tokens" class="form-label">Max Tokens</label>
                        <input type="number" class="form-control" id="max_tokens" name="max_tokens" value="{{ config.ollama_settings.max_tokens }}">
                        <div class="form-text">Maximum number of tokens to generate for each response.</div>
                    </div>
                    <button type="submit" class="btn btn-primary">Save Settings</button>
                </form>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const temperatureSlider = document.getElementById('temperature');
        const temperatureValue = document.getElementById('temperature-value');
        
        temperatureSlider.addEventListener('input', function() {
            temperatureValue.textContent = this.value;
        });
    </script>
</body>
</html>
EOF

# Create CSS file
cat > static/css/styles.css << 'EOF'
body {
    background-color: #f8f9fa;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.navbar-brand {
    font-weight: bold;
    letter-spacing: 1px;
}

.card {
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
}

.card-header {
    background-color: #f1f8ff;
    border-bottom: 1px solid rgba(0, 0, 0, 0.125);
}

.task-item {
    transition: all 0.3s ease;
}

.task-item:hover {
    background-color: #f1f8ff;
}

.task-item.active {
    background-color: #e2f0fd;
    border-color: #90c8f8;
}

.alert-processing {
    background-color: #fff8e1;
    border-color: #ffe082;
    color: #ff8f00;
}

.alert-completed {
    background-color: #e8f5e9;
    border-color: #a5d6a7;
    color: #2e7d32;
}

.alert-error {
    background-color: #ffebee;
    border-color: #ef9a9a;
    color: #c62828;
}
EOF

# Create JavaScript file
cat > static/js/main.js << 'EOF'
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const uploadForm = document.getElementById('upload-form');
    const uploadProgress = document.getElementById('upload-progress');
    const taskSection = document.getElementById('task-section');
    const currentTaskInfo = document.getElementById('current-task-info');
    const mimicSection = document.getElementById('mimic-section');
    const mimicForm = document.getElementById('mimic-form');
    const sourceTaskId = document.getElementById('source-task-id');
    const resultSection = document.getElementById('result-section');
    const resultContent = document.getElementById('result-content');
    const taskHistory = document.getElementById('task-history');
    
    // State
    let statusPollInterval;
    let latestIngestTaskId = null;
    
    // Start polling for status
    startStatusPolling();
    
    // Event listeners
    uploadForm.addEventListener('submit', handleUpload);
    mimicForm.addEventListener('submit', handleMimic);
    
    // Handle file selection from desktop app
    document.addEventListener('fileSelected', function(e) {
        const filePath = e.detail.filePath;
        console.log('File selected event received:', filePath);
        
        // Create a FormData with the file path
        const formData = new FormData();
        formData.append('file_path', filePath);
        
        uploadProgress.classList.remove('d-none');
        
        fetch('/upload?desktop=true', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            latestIngestTaskId = data.task_id;
        })
        .catch(error => {
            console.error('Error uploading file:', error);
            alert('Error uploading file');
            uploadProgress.classList.add('d-none');
        });
    });
    
    // Functions
    function handleUpload(event) {
        event.preventDefault();
        
        const fileInput = document.getElementById('file');
        if (!fileInput.files.length) {
            alert('Please select a file to upload');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        uploadProgress.classList.remove('d-none');
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            latestIngestTaskId = data.task_id;
            fileInput.value = '';
        })
        .catch(error => {
            console.error('Error uploading file:', error);
            alert('Error uploading file');
            uploadProgress.classList.add('d-none');
        });
    }
    
    function handleMimic(event) {
        event.preventDefault();
        
        const targetLanguage = document.getElementById('target-language').value;
        
        const formData = new FormData();
        formData.append('source_task_id', sourceTaskId.value);
        formData.append('target_language', targetLanguage);
        
        mimicSection.classList.add('d-none');
        uploadProgress.classList.remove('d-none');
        
        fetch('/mimic', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log('Mimic task initiated:', data.task_id);
        })
        .catch(error => {
            console.error('Error initiating mimic task:', error);
            alert('Error initiating mimic task');
            uploadProgress.classList.add('d-none');
        });
    }
    
    function startStatusPolling() {
        statusPollInterval = setInterval(fetchStatus, 2000);
    }
    
    function fetchStatus() {
        fetch('/status')
            .then(response => response.json())
            .then(data => {
                updateTaskStatus(data);
                updateTaskHistory(data.tasks);
            })
            .catch(error => {
                console.error('Error fetching status:', error);
            });
    }
    
    function updateTaskStatus(data) {
        if (data.current_task) {
            taskSection.classList.remove('d-none');
            uploadProgress.classList.remove('d-none');
            
            const task = data.current_task;
            let statusHtml = `
                <div class="alert alert-processing">
                    <h5>Processing ${task.type === 'ingest' ? 'Ingestion' : 'Mimicry'} Task</h5>
                    <p>Task ID: ${task.id}</p>
                    <p>Status: ${task.status}</p>
                    <div class="progress">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" style="width: 100%"></div>
                    </div>
                </div>
            `;
            
            currentTaskInfo.innerHTML = statusHtml;
        } else {
            uploadProgress.classList.add('d-none');
            
            const completedTasks = data.tasks.filter(task => task.status === 'completed');
            if (completedTasks.length > 0) {
                const latestCompletedTask = completedTasks[completedTasks.length - 1];
                
                if (latestCompletedTask.id === latestIngestTaskId) {
                    mimicSection.classList.remove('d-none');
                    sourceTaskId.value = latestIngestTaskId;
                    latestIngestTaskId = null;
                }
            }
        }
    }
    
    function updateTaskHistory(tasks) {
        if (!tasks || tasks.length === 0) {
            taskHistory.innerHTML = '<p>No tasks yet</p>';
            return;
        }
        
        taskHistory.innerHTML = '';
        
        const sortedTasks = [...tasks].sort((a, b) => b.timestamp - a.timestamp);
        
        sortedTasks.forEach(task => {
            let statusClass = '';
            let statusText = task.status;
            
            if (task.status === 'completed') {
                statusClass = 'text-success';
                statusText = 'Completed';
            } else if (task.status === 'processing') {
                statusClass = 'text-warning';
                statusText = 'Processing...';
            } else if (task.status === 'error') {
                statusClass = 'text-danger';
                statusText = 'Error';
            }
            
            const taskTime = new Date(task.timestamp * 1000).toLocaleString();
            const taskTypeName = task.type === 'ingest' ? 'Ingestion' : 'Mimicry';
            
            let taskItemHtml = `
                <div class="list-group-item task-item">
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">${taskTypeName} Task</h5>
                        <small>${taskTime}</small>
                    </div>
                    <p class="mb-1">ID: ${task.id}</p>
                    <p class="mb-1 ${statusClass}">Status: ${statusText}</p>
            `;
            
            if (task.status === 'completed') {
                taskItemHtml += '<div class="mt-2">';
                
                if (task.type === 'ingest') {
                    taskItemHtml += `
                        <a href="/download/${task.id}/specs" class="btn btn-sm btn-outline-primary me-2">Download Specs</a>
                        <a href="/download/${task.id}/reconstructed" class="btn btn-sm btn-outline-success">Download Reconstructed</a>
                    `;
                } else if (task.type === 'mimic') {
                    taskItemHtml += `
                        <a href="/download/${task.id}/mimicked" class="btn btn-sm btn-outline-primary">Download Mimicked (${task.target_language})</a>
                    `;
                }
                
                taskItemHtml += '</div>';
            }
            
            if (task.status === 'error' && task.error) {
                taskItemHtml += `<p class="text-danger mt-2">Error: ${task.error}</p>`;
            }
            
            taskItemHtml += '</div>';
            
            taskHistory.innerHTML += taskItemHtml;
        });
    }
});
EOF

echo "Templates and static files created successfully."
