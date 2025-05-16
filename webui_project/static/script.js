// static/script.js
let validatedFiles = {
    md: null,
    csv: null
};

async function validateFile(file, fileType) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);

    try {
        const response = await fetch('/validate-file', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        const statusElement = document.getElementById(`${fileType}FileStatus`);

        if (result.status === 'success') {
            statusElement.innerHTML = `<div class="alert alert-success">✓ 文件验证通过</div>`;
            validatedFiles[fileType] = result.file_path;
            
            // 更新配置状态显示（如果是md文件）
            if (fileType === 'md' && 'preserve_structure' in result) {
                const structureStatus = document.getElementById('structureStatus');
                if (structureStatus) {
                    structureStatus.innerHTML = `文档结构保留: ${result.preserve_structure ? '是' : '否'}`;
                }
            }
        } else {
            statusElement.innerHTML = `<div class="alert alert-danger">✗ ${result.message}</div>`;
            validatedFiles[fileType] = null;
        }

        updateProcessButton();

    } catch (error) {
        console.error('Error:', error);
        document.getElementById(`${fileType}FileStatus`).innerHTML = 
            `<div class="alert alert-danger">✗ 验证过程出错</div>`;
        validatedFiles[fileType] = null;
    }
}

function updateProcessButton() {
    const processBtn = document.getElementById('processBtn');
    processBtn.disabled = !(validatedFiles.md && validatedFiles.csv);
}

document.getElementById('validateMdBtn').addEventListener('click', () => {
    const file = document.getElementById('mdFile').files[0];
    if (file) validateFile(file, 'md');
});

document.getElementById('validateCsvBtn').addEventListener('click', () => {
    const file = document.getElementById('csvFile').files[0];
    if (file) validateFile(file, 'csv');
});

document.getElementById('processBtn').addEventListener('click', async () => {
    const progressBar = document.getElementById('progressBar');
    const progressBarInner = progressBar.querySelector('.progress-bar');
    const result = document.getElementById('result');

    try {
        progressBar.classList.remove('d-none');

        const formData = new FormData();
        formData.append('md_path', validatedFiles.md);
        formData.append('csv_path', validatedFiles.csv);
        formData.append('llm_provider', document.getElementById('llmProvider').value);

        const response = await fetch('/process', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('处理失败');

        const data = await response.json();
        result.classList.remove('d-none');
        document.getElementById('downloadLink').href = data.output_file;

    } catch (error) {
        alert('处理失败：' + error.message);
    } finally {
        progressBar.classList.add('d-none');
    }
});

// 文件输入改变时重置验证状态
document.getElementById('mdFile').addEventListener('change', () => {
    validatedFiles.md = null;
    document.getElementById('mdFileStatus').innerHTML = '';
    updateProcessButton();
});

document.getElementById('csvFile').addEventListener('change', () => {
    validatedFiles.csv = null;
    document.getElementById('csvFileStatus').innerHTML = '';
    updateProcessButton();
});
