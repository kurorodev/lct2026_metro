// Human review is deliberately opt-in. No predictions become reference labels.
let reviewLabels = {}, reviewKey = '';
function labelStoreKey() {
  return 'metro-guard-review:' + summary.bag.split(/[\\/]/).pop() + ':' + frames[0].bag_timestamp;
}
function loadReview() {
  reviewKey = labelStoreKey();
  try { reviewLabels = JSON.parse(localStorage.getItem(reviewKey) || '{}'); }
  catch { reviewLabels = {}; }
  refreshReview();
}
function refreshReview() {
  if (!frames.length) return;
  const label = reviewLabels[frames[idx].frame_index];
  document.getElementById('review-state').textContent = !label ? 'Кадр не размечен' :
    label.obstacle_present === true ? 'Метка: есть препятствие' :
    label.obstacle_present === false ? 'Метка: нет видимого препятствия' : 'Метка: не определено';
  document.getElementById('label-distance').value = label?.nearest_distance_m ?? '';
  document.getElementById('label-note').value = label?.note ?? '';
  document.getElementById('review-count').textContent = Object.values(reviewLabels).filter(x => x.obstacle_present !== null).length + ' проверенных кадров';
}
function saveLabel(present) {
  if (!frames.length) return;
  const distance = document.getElementById('label-distance').value;
  const nearest = distance === '' || present !== true ? null : Number(distance);
  if (nearest !== null && (!Number.isFinite(nearest) || nearest < 0)) {
    document.getElementById('error').textContent = 'Расстояние должно быть неотрицательным числом.'; return;
  }
  const f = frames[idx];
  reviewLabels[f.frame_index] = {frame_index:f.frame_index, bag_timestamp:f.bag_timestamp,
    bag_name:summary.bag.split(/[\\/]/).pop(), obstacle_present:present, nearest_distance_m:nearest,
    note:document.getElementById('label-note').value, source:'manual_review'};
  try { localStorage.setItem(reviewKey, JSON.stringify(reviewLabels)); }
  catch { document.getElementById('error').textContent = 'Браузер не сохранил метки. Скачайте JSONL перед закрытием.'; }
  refreshReview();
}
document.getElementById('hide-detections').onchange = event => {
  hideDetections = event.target.checked; update();
};
document.querySelectorAll('[data-label]').forEach(button => button.onclick = () => {
  saveLabel(button.dataset.label === 'yes' ? true : button.dataset.label === 'no' ? false : null);
});
document.getElementById('download-labels').onclick = () => {
  const rows = Object.values(reviewLabels).sort((a,b) => a.frame_index-b.frame_index);
  if (!rows.length) { document.getElementById('error').textContent = 'Сначала разметьте хотя бы один кадр.'; return; }
  const url = URL.createObjectURL(new Blob([rows.map(row => JSON.stringify(row)).join('\n')+'\n'], {type:'application/x-ndjson'}));
  const link = document.createElement('a'); link.href = url;
  link.download = (summary.bag.split(/[\\/]/).pop() || 'bag') + '.labels.jsonl';
  link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
};
