// static/js/debug-checkboxes.js
/**
 * Debug Script for Checkbox Issue
 *
 * Run this in browser console to diagnose checkbox data-file-id problem
 */

console.log('=== DocAI Checkbox Debug ===');

// Get all checkboxes
const sourceList = document.getElementById('sourceList');
const allCheckboxes = sourceList.querySelectorAll('input[type="checkbox"]');
const checkedCheckboxes = sourceList.querySelectorAll('input[type="checkbox"]:checked');

console.log('Total checkboxes:', allCheckboxes.length);
console.log('Checked checkboxes:', checkedCheckboxes.length);

// Inspect each checkbox
allCheckboxes.forEach((checkbox, index) => {
    const listItem = checkbox.closest('.source-item');
    const fileName = listItem?.querySelector('.file-name')?.textContent || 'Unknown';

    console.log(`\nCheckbox ${index + 1}:`);
    console.log('  File name:', fileName);
    console.log('  Checked:', checkbox.checked);
    console.log('  data-file-id:', checkbox.dataset.fileId);
    console.log('  All dataset:', checkbox.dataset);
    console.log('  HTML:', checkbox.outerHTML);
});

// Try to get selected file IDs
const fileIds = Array.from(checkedCheckboxes)
    .map(cb => cb.dataset.fileId)
    .filter(id => id);

console.log('\n=== Result ===');
console.log('Selected file IDs:', fileIds);

if (checkedCheckboxes.length > 0 && fileIds.length === 0) {
    console.error('❌ PROBLEM FOUND: Checkboxes are checked but have no data-file-id!');
    console.log('\n=== Possible Causes ===');
    console.log('1. Upload response did not include file_id');
    console.log('2. updateFileStatus() was called without file_id parameter');
    console.log('3. Checkbox was created manually without data-file-id');

    // Check if this is a pre-existing checkbox (from before upload)
    const firstCheckbox = checkedCheckboxes[0];
    const listItem = firstCheckbox.closest('.source-item');
    const hasSpinner = !!listItem.querySelector('.spinner');

    console.log('\n=== Diagnosis ===');
    console.log('Has spinner:', hasSpinner);

    if (!hasSpinner) {
        console.log('Status: Checkbox replaced spinner (upload completed)');
        console.log('Issue: Upload response likely missing file_id field');
        console.log('\n=== Action Required ===');
        console.log('1. Check upload API response structure');
        console.log('2. Verify backend returns {file_id: "...", ...}');
        console.log('3. Check browser Network tab for /api/v1/upload response');
    }
} else if (fileIds.length > 0) {
    console.log('✅ Checkboxes have file IDs correctly!');
    console.log('Issue might be elsewhere (e.g., validation logic)');
}

console.log('\n=== End Debug ===');
