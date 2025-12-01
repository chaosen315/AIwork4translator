// static/script.js (root copy)
/* copied from webui_project/static/script.js */
let validatedFiles = { md: null, csv: null };
async function validateFile(file, fileType) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('file_type', fileType);
  try {
    const response = await fetch('/validate-file', { method: 'POST', body: formData });
    const result = await response.json();
    const statusElement = document.getElementById(`${fileType}FileStatus`);
    if (statusElement) {
      if (result.status === 'success') {
        statusElement.innerHTML = `<div class="alert alert-success">✓ 文件验证通过</div>`;
        validatedFiles[fileType] = result.file_path;
        if (fileType === 'md' && 'preserve_structure' in result) {
          const structureStatus = document.getElementById('structureStatus');
          if (structureStatus) {
            structureStatus.innerHTML = `文档结构保留: ${result.preserve_structure ? '是' : '否'}`;
          }
        }
        await saveToCache();
      } else {
        statusElement.innerHTML = `<div class="alert alert-danger">✗ ${result.message}</div>`;
        validatedFiles[fileType] = null;
        await saveToCache();
      }
    }
  } catch (error) {
    console.error('Error:', error);
    document.getElementById(`${fileType}FileStatus`).innerHTML = `<div class="alert alert-danger">✗ 验证过程出错</div>`;
    validatedFiles[fileType] = null;
    await saveToCache();
  }
}
async function saveToCache() {
  try {
    const response = await fetch('/prepare-editor', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ md_path: validatedFiles.md || '', csv_path: validatedFiles.csv || '', llm_provider: document.getElementById('llmProvider').value || '' })
    });
    const result = await response.json();
    if (result.status === 'success') { console.log('文件信息已保存到缓存'); }
  } catch (error) { console.error('保存到缓存失败:', error); }
}
const validateMdBtn = document.getElementById('validateMdBtn');
if (validateMdBtn) { validateMdBtn.addEventListener('click', () => { const mdFile = document.getElementById('mdFile'); if (mdFile && mdFile.files && mdFile.files[0]) { validateFile(mdFile.files[0], 'md'); } }); }
const validateCsvBtn = document.getElementById('validateCsvBtn');
if (validateCsvBtn) { validateCsvBtn.addEventListener('click', () => { const csvFile = document.getElementById('csvFile'); if (csvFile && csvFile.files && csvFile.files[0]) { validateFile(csvFile.files[0], 'csv'); } }); }
const editorBtn = document.getElementById('editorBtn');
if (editorBtn) { editorBtn.addEventListener('click', async () => { if (!validatedFiles.md) { alert('请先上传并验证原文文件'); return; } await saveToCache(); window.location.href = '/editor?cache_key=0'; }); }
async function testApiConnection() {
  const llmProvider = document.getElementById('llmProvider'); if (!llmProvider) { console.error('llmProvider element not found'); return; }
  const provider = llmProvider.value; const formData = new FormData(); formData.append('llm_provider', provider);
  try { const response = await fetch('/test-api', { method: 'POST', body: formData }); const data = await response.json(); if (data.status === 'error') { alert('API测试失败：' + data.error); } else { console.log('API测试完成', data.test_results); } } catch (error) { console.error('API测试错误:', error); alert('API测试失败：' + error.message); }
}
const mdFile = document.getElementById('mdFile'); if (mdFile) { mdFile.addEventListener('change', () => { const mdFileStatus = document.getElementById('mdFileStatus'); if (mdFileStatus) { mdFileStatus.innerHTML = ''; } validatedFiles.md = null; }); }
const csvFile = document.getElementById('csvFile'); if (csvFile) { csvFile.addEventListener('change', () => { const csvFileStatus = document.getElementById('csvFileStatus'); if (csvFileStatus) { csvFileStatus.innerHTML = ''; } validatedFiles.csv = null; }); }
async function initFromCache() {
  try { const res = await fetch('/get-latest-cache'); const data = await res.json(); if (data.status === 'success') { if (data.csv_path) { validatedFiles.csv = data.csv_path; const statusElement = document.getElementById('csvFileStatus'); if (statusElement) { const name = data.csv_path.split(/[\\/]/).pop(); statusElement.innerHTML = `<div class="alert alert-success">✓ 已加载缓存词典：${name}</div>`; } } const llmProvider = document.getElementById('llmProvider'); if (llmProvider && data.llm_provider) { llmProvider.value = data.llm_provider; } } else { const statusElement = document.getElementById('csvFileStatus'); if (statusElement) { statusElement.innerHTML = `<div class="alert alert-warning">未获取到缓存数据</div>`; } } } catch (e) { console.error('[index]initFromCache:error', e); const statusElement = document.getElementById('csvFileStatus'); if (statusElement) { statusElement.innerHTML = `<div class="alert alert-danger">读取缓存失败：${e?.message || e}</div>`; } }
}
if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', initFromCache); } else { initFromCache(); }
