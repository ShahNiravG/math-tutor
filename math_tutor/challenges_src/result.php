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
            --accent:#a14d2e; --line:#d8cfc2; --green:#166534; --green-bg:#dcfce7; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Georgia,"Times New Roman",serif; color:var(--ink);
           background:linear-gradient(180deg,#f6efe3 0%,var(--bg) 100%); }
    .page { width:min(860px,calc(100vw - 32px)); margin:32px auto 64px; }
    .header-card { background:var(--paper); border:1px solid var(--line); border-radius:18px;
                   padding:28px 32px; margin-bottom:24px;
                   box-shadow:0 8px 24px rgba(78,55,32,.07); }
    .header-card h1 { margin:0 0 8px; font-size:1.9rem; }
    .meta { display:flex; flex-wrap:wrap; gap:12px; margin-top:12px; }
    .chip { display:inline-block; padding:5px 12px; border-radius:999px;
            background:var(--green-bg); color:var(--green); font-size:.88rem; font-weight:600; }
    .chip-time { background:#fef9c3; color:#854d0e; }
    .chip-date { background:#e2e8f0; color:#334155; font-weight:400; }
    .actions { margin-top:16px; display:flex; gap:10px; flex-wrap:wrap; }
    .btn { appearance:none; border:1px solid var(--line); background:#fff; color:var(--accent);
           font:inherit; font-weight:600; padding:9px 16px; border-radius:999px; cursor:pointer;
           text-decoration:none; }
    .btn:hover { background:var(--accent); color:#fff; }
    .q-card { background:var(--paper); border:1px solid var(--line); border-radius:16px;
              padding:24px 28px; margin-bottom:16px;
              box-shadow:0 4px 12px rgba(78,55,32,.05); }
    .q-header { display:flex; align-items:baseline; justify-content:space-between;
                flex-wrap:wrap; gap:8px; margin-bottom:14px; }
    .q-num { font-size:1rem; font-weight:700; color:var(--accent); }
    .q-source { font-size:.82rem; color:var(--muted); font-family:system-ui,sans-serif; }
    .q-text { line-height:1.75; margin-bottom:18px; }
    .q-text p { margin:.4em 0; }
    .q-text strong { color:#213647; }
    .answer-label { font-size:.85rem; font-weight:700; color:var(--muted);
                    text-transform:uppercase; letter-spacing:.06em; margin-bottom:8px; }
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
      <span class="chip">&#10003; <?= count($answers) ?> questions</span>
      <span class="chip chip-time">&#9201; <?= $time_fmt ?></span>
      <span class="chip chip-date"><?= $submitted ?></span>
      <?php if ($user_email): ?>
      <span class="chip chip-date">&#128100; <?= $user_email ?></span>
      <?php endif; ?>
    </div>
    <div class="actions">
      <a class="btn" href="index.html">&#8592; All Exams</a>
      <button class="btn" onclick="window.print()">Print / Save PDF</button>
    </div>
  </div>

  <?php foreach ($answers as $i => $item): ?>
  <?php
    $qnum   = $i + 1;
    $source = htmlspecialchars($item['source_label'] ?? '');
    $qtext  = $item['question_text'] ?? '';
    $ans    = trim($item['answer'] ?? '');
  ?>
  <div class="q-card">
    <div class="q-header">
      <span class="q-num">Question <?= $qnum ?></span>
      <span class="q-source"><?= $source ?></span>
    </div>
    <div class="q-text" id="qt-<?= $qnum ?>"></div>
    <div class="answer-label">Your Answer</div>
    <div class="answer-box <?= $ans === '' ? 'answer-empty' : '' ?>">
      <?= $ans === '' ? 'No answer given' : htmlspecialchars($ans) ?>
    </div>
  </div>
  <script>
    (function() {
      var el = document.getElementById('qt-<?= $qnum ?>');
      var raw = <?= json_encode($qtext) ?>;
      el.innerHTML = mdToHtml(raw);
      if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([el]);
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
