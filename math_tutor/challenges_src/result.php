<?php
require_once __DIR__ . '/config.php';

$token = $_GET['token'] ?? '';
if (!preg_match('/^[a-f0-9]{12}$/', $token)) {
    http_response_code(404);
    die('<h1>Result not found</h1>');
}

try {
    $pdo = new PDO(
        'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
        DB_USER, DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    $stmt = $pdo->prepare("SELECT * FROM challenge_results WHERE token = ?");
    $stmt->execute([$token]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    http_response_code(500);
    die('<h1>Database error</h1>');
}

if (!$row) {
    http_response_code(404);
    die('<h1>Result not found</h1>');
}

$exam_title  = htmlspecialchars($row['exam_title']);
$submitted   = htmlspecialchars($row['submitted_at']);
$secs        = (int)$row['time_seconds'];
$time_fmt    = sprintf('%d:%02d', intdiv($secs, 60), $secs % 60);
$answers     = json_decode($row['answers_json'], true) ?: [];
$user_email  = htmlspecialchars($row['user_email'] ?? '');

// Calculate score from MCQ answers
$score = 0;
$total_q = count($answers);
foreach ($answers as $item) {
    if (!empty($item['answer']) && !empty($item['correct']) && $item['answer'] === $item['correct']) {
        $score++;
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><?= $exam_title ?> — Result</title>
  <script>window.MathJax={tex:{inlineMath:[['\\(','\\)'],['$','$']],displayMath:[['\\[','\\]'],['$$','$$']]}};</script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <style>
    :root { --bg:#f5f1e8; --paper:#fffaf2; --ink:#1f2a33; --muted:#5b6a74;
            --accent:#a14d2e; --line:#d8cfc2;
            --correct:#166534; --correct-bg:#dcfce7;
            --wrong:#dc2626;   --wrong-bg:#fee2e2; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Georgia,"Times New Roman",serif; color:var(--ink);
           background:linear-gradient(180deg,#f6efe3 0%,var(--bg) 100%); }
    .page { width:min(860px,calc(100vw - 32px)); margin:32px auto 64px; }

    /* ── Header card ── */
    .header-card { background:var(--paper); border:1px solid var(--line); border-radius:18px;
                   padding:28px 32px; margin-bottom:24px;
                   box-shadow:0 8px 24px rgba(78,55,32,.07); }
    .header-card h1 { margin:0 0 8px; font-size:1.9rem; }
    .meta { display:flex; flex-wrap:wrap; gap:10px; margin-top:12px; }
    .chip { display:inline-block; padding:5px 12px; border-radius:999px;
            font-size:.88rem; font-weight:600; font-family:system-ui,sans-serif; }
    .chip-score-perfect { background:var(--correct-bg); color:var(--correct); }
    .chip-score-partial { background:#fef9c3; color:#854d0e; }
    .chip-score-low     { background:var(--wrong-bg); color:var(--wrong); }
    .chip-time  { background:#fef9c3; color:#854d0e; font-weight:400; }
    .chip-date  { background:#e2e8f0; color:#334155; font-weight:400; }
    .chip-email { background:#e2e8f0; color:#334155; font-weight:400; }
    .actions { margin-top:16px; display:flex; gap:10px; flex-wrap:wrap; }
    .btn { appearance:none; border:1px solid var(--line); background:#fff; color:var(--accent);
           font:inherit; font-weight:600; padding:9px 16px; border-radius:999px; cursor:pointer;
           text-decoration:none; font-size:.95rem; }
    .btn:hover { background:var(--accent); color:#fff; }

    /* ── Question cards ── */
    .q-card { background:var(--paper); border:1px solid var(--line); border-radius:16px;
              padding:24px 28px; margin-bottom:16px;
              box-shadow:0 4px 12px rgba(78,55,32,.05);
              border-left:4px solid var(--line); }
    .q-card.result-correct { border-left-color:var(--correct); }
    .q-card.result-wrong   { border-left-color:var(--wrong); }
    .q-card.result-skipped { border-left-color:#9ca3af; }
    .q-header { display:flex; align-items:baseline; justify-content:space-between;
                flex-wrap:wrap; gap:8px; margin-bottom:14px; }
    .q-num { font-size:1rem; font-weight:700; color:var(--accent);
             display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
    .badge { padding:2px 10px; border-radius:999px; font-size:.78rem; font-weight:700;
             font-family:system-ui,sans-serif; }
    .badge-correct { background:var(--correct-bg); color:var(--correct); }
    .badge-wrong   { background:var(--wrong-bg);   color:var(--wrong); }
    .badge-skipped { background:#f3f4f6; color:#6b7280; }
    .q-source { font-size:.82rem; color:var(--muted); font-family:system-ui,sans-serif; }
    .q-text { line-height:1.75; margin-bottom:18px; font-size:1.05rem; }
    .q-text p { margin:.4em 0; }
    .q-text strong { color:#213647; }

    /* ── MCQ result options ── */
    .answer-label { font-size:.82rem; font-weight:700; color:var(--muted);
                    text-transform:uppercase; letter-spacing:.06em; margin-bottom:8px;
                    font-family:system-ui,sans-serif; }
    .mcq-result { display:flex; flex-direction:column; gap:8px; }
    .mcq-result-opt { display:flex; align-items:flex-start; gap:12px; padding:10px 14px;
                      border:1.5px solid var(--line); border-radius:10px;
                      font-size:.95rem; line-height:1.6; }
    .mcq-result-opt.opt-correct { border-color:var(--correct); background:var(--correct-bg); }
    .mcq-result-opt.opt-correct .opt-letter { color:var(--correct); }
    .mcq-result-opt.opt-wrong   { border-color:var(--wrong);   background:var(--wrong-bg); }
    .mcq-result-opt.opt-wrong   .opt-letter { color:var(--wrong); }
    .mcq-result-opt.opt-reveal  { border-color:var(--correct); background:var(--correct-bg); opacity:.8; }
    .mcq-result-opt.opt-reveal  .opt-letter { color:var(--correct); }
    .opt-letter { min-width:28px; font-weight:700; font-family:system-ui,sans-serif;
                  color:var(--muted); flex-shrink:0; padding-top:1px; }
    .opt-text { flex:1; }
    .opt-text p { margin:0; }

    /* ── Legacy text answer (pre-MCQ submissions) ── */
    .answer-box { background:#f9f7f3; border:1px solid var(--line); border-radius:10px;
                  padding:14px 16px; line-height:1.65; min-height:48px;
                  white-space:pre-wrap; font-family:Georgia,serif; }
    .answer-empty { color:var(--muted); font-style:italic; }

    @media print {
      body { background:#fff; }
      .actions, .btn { display:none !important; }
      .page { width:100%; margin:0; }
      .header-card, .q-card { box-shadow:none; border:1px solid #ccc; }
    }
  </style>
</head>
<body>
<div class="page">
  <div class="header-card">
    <h1><?= $exam_title ?> — Result</h1>
    <div class="meta">
      <?php
        $pct = $total_q > 0 ? $score / $total_q : 0;
        $score_class = $pct >= 1.0 ? 'chip-score-perfect' : ($pct >= 0.6 ? 'chip-score-partial' : 'chip-score-low');
      ?>
      <span class="chip <?= $score_class ?>">&#127942; <?= $score ?>/<?= $total_q ?> correct</span>
      <span class="chip chip-time">&#9201; <?= $time_fmt ?></span>
      <span class="chip chip-date"><?= $submitted ?></span>
      <?php if ($user_email): ?>
      <span class="chip chip-email">&#128100; <?= $user_email ?></span>
      <?php endif; ?>
    </div>
    <div class="actions">
      <a class="btn" href="index.html">&#8592; All Exams</a>
      <button class="btn" onclick="window.print()">Print / Save PDF</button>
    </div>
  </div>

  <?php foreach ($answers as $i => $item): ?>
  <?php
    $qnum    = $i + 1;
    $source  = htmlspecialchars($item['source_label'] ?? '');
    $qtext   = $item['question_text'] ?? '';
    $options = $item['options'] ?? [];   // present in MCQ submissions
    $correct = $item['correct'] ?? '';
    $ans     = $item['answer'] ?? '';

    $is_correct = ($ans !== '' && $ans === $correct);
    $is_wrong   = ($ans !== '' && $ans !== $correct);
    $is_skipped = ($ans === '');
    $card_cls   = $is_correct ? 'result-correct' : ($is_wrong ? 'result-wrong' : 'result-skipped');
  ?>
  <div class="q-card <?= $card_cls ?>">
    <div class="q-header">
      <span class="q-num">
        Question <?= $qnum ?>
        <?php if ($is_correct): ?><span class="badge badge-correct">&#10003; Correct</span><?php endif; ?>
        <?php if ($is_wrong):   ?><span class="badge badge-wrong">&#10007; Wrong</span><?php endif; ?>
        <?php if ($is_skipped): ?><span class="badge badge-skipped">&mdash; Skipped</span><?php endif; ?>
      </span>
      <span class="q-source"><?= $source ?></span>
    </div>
    <div class="q-text" id="qt-<?= $qnum ?>"></div>

    <?php if (!empty($options)): ?>
    <div class="answer-label">Options</div>
    <div class="mcq-result" id="opts-<?= $qnum ?>">
      <?php foreach ($options as $optStr): ?>
      <?php
        preg_match('/^\(([A-D])\)\s*([\s\S]*)/', $optStr, $m);
        $letter   = $m[1] ?? '?';
        $opt_text = isset($m[2]) ? trim($m[2]) : $optStr;
        $opt_cls  = '';
        $icon     = $letter;
        if ($letter === $correct && $letter === $ans)      { $opt_cls = 'opt-correct'; $icon = '&#10003; '.$letter; }
        elseif ($letter === $ans && $letter !== $correct)  { $opt_cls = 'opt-wrong';   $icon = '&#10007; '.$letter; }
        elseif ($letter === $correct)                      { $opt_cls = 'opt-reveal';  $icon = '&#10003; '.$letter; }
      ?>
      <div class="mcq-result-opt <?= $opt_cls ?>">
        <span class="opt-letter"><?= $icon ?></span>
        <span class="opt-text" data-raw="<?= htmlspecialchars($opt_text) ?>"></span>
      </div>
      <?php endforeach; ?>
    </div>
    <?php elseif ($ans !== ''): ?>
    <!-- Legacy: free-text answer (pre-MCQ submissions) -->
    <div class="answer-label">Your Answer</div>
    <div class="answer-box"><?= htmlspecialchars($ans) ?></div>
    <?php else: ?>
    <div class="answer-label">Your Answer</div>
    <div class="answer-box answer-empty">No answer given</div>
    <?php endif; ?>
  </div>
  <script>
  (function() {
    var qEl = document.getElementById('qt-<?= $qnum ?>');
    qEl.innerHTML = mdToHtml(<?= json_encode($qtext) ?>);
    <?php if (!empty($options)): ?>
    document.querySelectorAll('#opts-<?= $qnum ?> .opt-text[data-raw]').forEach(function(el){
      el.innerHTML = mdToHtml(el.dataset.raw);
      el.removeAttribute('data-raw');
    });
    if (window.MathJax && MathJax.typesetPromise) {
      MathJax.typesetPromise([qEl, document.getElementById('opts-<?= $qnum ?>')]);
    }
    <?php else: ?>
    if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([qEl]);
    <?php endif; ?>
  })();
  </script>
  <?php endforeach; ?>
</div>

<script>
function mdToHtml(text) {
  var dm = [], im = [];
  text = text.replace(/\\\[[\s\S]*?\\\]/g, function(m){ dm.push(m); return '\x00DM'+(dm.length-1)+'\x00'; });
  text = text.replace(/\\\([\s\S]*?\\\)|\$[^$\n]+\$/g, function(m){ im.push(m); return '\x00IM'+(im.length-1)+'\x00'; });
  text = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  text = text.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  text = text.replace(/\n\n+/g,'</p><p>').replace(/\n/g,'<br>');
  dm.forEach(function(m,i){ text = text.replace('\x00DM'+i+'\x00', m); });
  im.forEach(function(m,i){ text = text.replace('\x00IM'+i+'\x00', m); });
  return '<p>'+text+'</p>';
}
</script>
</body>
</html>
