<?php
require_once __DIR__ . '/config.php';

$email   = $_GET['email']   ?? '';
$exam_id = $_GET['exam_id'] ?? '';

if (!$email || !$exam_id) {
    http_response_code(400);
    die('<h1>Missing parameters</h1>');
}

$exam_id = substr(preg_replace('/[^a-z0-9-]/', '', $exam_id), 0, 32);

try {
    $pdo = new PDO(
        'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
        DB_USER, DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    $stmt = $pdo->prepare(
        "SELECT * FROM challenge_progress WHERE user_email = ? AND exam_id = ? LIMIT 1"
    );
    $stmt->execute([$email, $exam_id]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    http_response_code(500);
    die('<h1>Database error</h1>');
}

if (!$row) {
    http_response_code(404);
    die('<h1>In-progress exam not found</h1>');
}

$exam_title   = htmlspecialchars($row['exam_title']);
$user_email   = htmlspecialchars($row['user_email']);
$last_saved   = htmlspecialchars($row['last_saved_at']);
$secs         = (int)$row['timer_secs'];
$time_fmt     = sprintf('%d:%02d', intdiv($secs, 60), $secs % 60);
$answered_cnt = (int)$row['answered_count'];
$current_idx  = (int)$row['current_idx'];
$answers      = json_decode($row['answers_json'] ?? 'null', true) ?: [];

$total_q = count($answers);
$score   = 0;
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
  <title><?= $exam_title ?> — Partial Result</title>
  <script>window.MathJax={tex:{inlineMath:[['\\(','\\)'],['$','$']],displayMath:[['\\[','\\]'],['$$','$$']]}};</script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
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
  function normalizeOptionMath(text) {
    var raw = String(text || '').trim();
    if (!raw) return raw;
    if (/\\\(|\\\)|\\\[|\\\]|\$/.test(raw)) return raw;
    if (/\\[A-Za-z]+/.test(raw) || /\^\{?[^}\s]+\}?/.test(raw)) return '\\(' + raw + '\\)';
    return raw;
  }
  </script>
  <style>
    :root { --bg:#f5f1e8; --paper:#fffaf2; --ink:#1f2a33; --muted:#5b6a74;
            --accent:#a14d2e; --line:#d8cfc2;
            --correct:#166534; --correct-bg:#dcfce7;
            --wrong:#dc2626;   --wrong-bg:#fee2e2;
            --amber:#92400e;   --amber-bg:#fef9c3; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Georgia,"Times New Roman",serif; color:var(--ink);
           background:linear-gradient(180deg,#f6efe3 0%,var(--bg) 100%); }
    .page { width:min(860px,calc(100vw - 32px)); margin:32px auto 64px; }

    .header-card { background:var(--paper); border:1px solid var(--line); border-radius:18px;
                   padding:28px 32px; margin-bottom:24px;
                   box-shadow:0 8px 24px rgba(78,55,32,.07); }
    .header-card h1 { margin:0 0 4px; font-size:1.9rem; }
    .partial-banner {
      display:inline-block; padding:4px 14px; border-radius:999px;
      background:var(--amber-bg); color:var(--amber);
      font-family:system-ui,sans-serif; font-size:.85rem; font-weight:700;
      margin-bottom:12px;
    }
    .meta { display:flex; flex-wrap:wrap; gap:10px; margin-top:12px; }
    .chip { display:inline-block; padding:5px 12px; border-radius:999px;
            font-size:.88rem; font-weight:600; font-family:system-ui,sans-serif; }
    .chip-progress { background:var(--amber-bg); color:var(--amber); }
    .chip-score-perfect { background:var(--correct-bg); color:var(--correct); }
    .chip-score-partial { background:var(--amber-bg); color:var(--amber); }
    .chip-score-low     { background:var(--wrong-bg); color:var(--wrong); }
    .chip-time  { background:var(--amber-bg); color:var(--amber); font-weight:400; }
    .chip-date  { background:#e2e8f0; color:#334155; font-weight:400; }
    .chip-email { background:#e2e8f0; color:#334155; font-weight:400; }
    .actions { margin-top:16px; display:flex; gap:10px; flex-wrap:wrap; }
    .btn { appearance:none; border:1px solid var(--line); background:#fff; color:var(--accent);
           font:inherit; font-weight:600; padding:9px 16px; border-radius:999px; cursor:pointer;
           text-decoration:none; font-size:.95rem; }
    .btn:hover { background:var(--accent); color:#fff; }

    .q-card { background:var(--paper); border:1px solid var(--line); border-radius:16px;
              padding:24px 28px; margin-bottom:16px;
              box-shadow:0 4px 12px rgba(78,55,32,.05);
              border-left:4px solid var(--line); }
    .q-card.result-correct { border-left-color:var(--correct); }
    .q-card.result-wrong   { border-left-color:var(--wrong); }
    .q-card.result-skipped { border-left-color:#9ca3af; }
    .q-card.result-unanswered { border-left-color:#d1d5db; opacity:.7; }
    .q-header { display:flex; align-items:baseline; justify-content:space-between;
                flex-wrap:wrap; gap:8px; margin-bottom:14px; }
    .q-num { font-size:1rem; font-weight:700; color:var(--accent);
             display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
    .badge { padding:2px 10px; border-radius:999px; font-size:.78rem; font-weight:700;
             font-family:system-ui,sans-serif; }
    .badge-correct   { background:var(--correct-bg); color:var(--correct); }
    .badge-wrong     { background:var(--wrong-bg);   color:var(--wrong); }
    .badge-skipped   { background:#f3f4f6; color:#6b7280; }
    .badge-current   { background:var(--amber-bg); color:var(--amber); }
    .badge-not-reached { background:#f3f4f6; color:#9ca3af; }
    .q-source { font-size:.82rem; color:var(--muted); font-family:system-ui,sans-serif; }
    .q-text { line-height:1.75; margin-bottom:18px; font-size:1.05rem; }
    .q-text p { margin:.4em 0; }

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
    <div class="partial-banner">&#9203; In Progress — Partial View</div>
    <h1><?= $exam_title ?></h1>
    <div class="meta">
      <span class="chip chip-progress">&#9203; <?= $answered_cnt ?>/<?= $total_q ?> answered &middot; Q<?= $current_idx + 1 ?></span>
      <?php if ($answered_cnt > 0):
        $pct = $score / $answered_cnt;
        $score_class = $pct >= 1.0 ? 'chip-score-perfect' : ($pct >= 0.6 ? 'chip-score-partial' : 'chip-score-low');
      ?>
      <span class="chip <?= $score_class ?>">&#128200; <?= $score ?>/<?= $answered_cnt ?> correct so far</span>
      <?php endif; ?>
      <span class="chip chip-time">&#9201; <?= $time_fmt ?> elapsed</span>
      <span class="chip chip-date">&#128197; Last saved <?= $last_saved ?></span>
      <span class="chip chip-email">&#128100; <?= $user_email ?></span>
    </div>
    <div class="actions">
      <a class="btn" href="reports.php">&#8592; Reports</a>
      <button class="btn" onclick="window.print()">Print / Save PDF</button>
    </div>
  </div>

  <?php if (empty($answers)): ?>
  <div style="text-align:center;color:var(--muted);padding:48px 24px;font-family:system-ui,sans-serif;">
    No answer data saved yet for this session. The student must answer at least one question and trigger a progress save.
  </div>
  <?php endif; ?>

  <?php foreach ($answers as $i => $item): ?>
  <?php
    $qnum    = $i + 1;
    $source  = htmlspecialchars($item['source_label'] ?? '');
    $qtext   = $item['question_text'] ?? '';
    $options = $item['options'] ?? [];
    $correct = $item['correct'] ?? '';
    $ans     = $item['answer'] ?? '';

    $is_correct    = ($ans !== '' && $ans === $correct);
    $is_wrong      = ($ans !== '' && $ans !== $correct);
    $is_skipped    = ($ans === '' && $i < $current_idx);
    $not_reached   = ($ans === '' && $i > $current_idx);
    $is_current    = ($ans === '' && $i === $current_idx);

    if ($is_correct)   $card_cls = 'result-correct';
    elseif ($is_wrong) $card_cls = 'result-wrong';
    elseif ($not_reached) $card_cls = 'result-unanswered';
    else               $card_cls = 'result-skipped';
  ?>
  <div class="q-card <?= $card_cls ?>">
    <div class="q-header">
      <span class="q-num">
        Question <?= $qnum ?>
        <?php if ($is_correct):   ?><span class="badge badge-correct">&#10003; Correct</span><?php endif; ?>
        <?php if ($is_wrong):     ?><span class="badge badge-wrong">&#10007; Wrong</span><?php endif; ?>
        <?php if ($is_skipped):   ?><span class="badge badge-skipped">&mdash; Skipped</span><?php endif; ?>
        <?php if ($is_current):   ?><span class="badge badge-current">&#9654; Current</span><?php endif; ?>
        <?php if ($not_reached):  ?><span class="badge badge-not-reached">Not reached</span><?php endif; ?>
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
        if ($ans !== '') {
          if ($letter === $correct && $letter === $ans)      { $opt_cls = 'opt-correct'; $icon = '&#10003; '.$letter; }
          elseif ($letter === $ans && $letter !== $correct)  { $opt_cls = 'opt-wrong';   $icon = '&#10007; '.$letter; }
          elseif ($letter === $correct)                      { $opt_cls = 'opt-reveal';  $icon = '&#10003; '.$letter; }
        }
      ?>
      <div class="mcq-result-opt <?= $opt_cls ?>">
        <span class="opt-letter"><?= $icon ?></span>
        <span class="opt-text" data-raw="<?= htmlspecialchars($opt_text) ?>"></span>
      </div>
      <?php endforeach; ?>
    </div>
    <?php elseif ($ans !== ''): ?>
    <div class="answer-label">Answer Given</div>
    <div class="answer-box"><?= htmlspecialchars($ans) ?></div>
    <?php else: ?>
    <div class="answer-label">Answer</div>
    <div class="answer-box answer-empty"><?= $not_reached ? 'Not reached yet' : ($is_current ? 'Currently on this question' : 'No answer given') ?></div>
    <?php endif; ?>
  </div>
  <script>
  (function() {
    var qEl = document.getElementById('qt-<?= $qnum ?>');
    qEl.innerHTML = mdToHtml(<?= json_encode($qtext) ?>);
    <?php if (!empty($options)): ?>
    document.querySelectorAll('#opts-<?= $qnum ?> .opt-text[data-raw]').forEach(function(el){
      el.innerHTML = mdToHtml(normalizeOptionMath(el.dataset.raw));
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

</body>
</html>
