<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/timezone.php';

$email   = $_GET['email']   ?? ($_SERVER['HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL'] ?? '');
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
$last_saved   = htmlspecialchars(challenge_format_california_timestamp($row['last_saved_at']));
$secs         = (int)$row['timer_secs'];
$time_fmt     = sprintf('%d:%02d', intdiv($secs, 60), $secs % 60);
$answered_cnt = (int)$row['answered_count'];
$current_idx  = (int)$row['current_idx'];
$answers      = json_decode($row['answers_json'] ?? 'null', true) ?: [];

$total_q = count($answers);
$current_question = $total_q > 0 ? min($total_q, $current_idx + 1) : ($current_idx + 1);
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
  <script src="experience.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
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
  function inlineMdToHtml(text) {
    return mdToHtml(text).replace(/^<p>/, '').replace(/<\/p>$/, '');
  }
  function normalizeOptionMath(text) {
    var raw = String(text || '').trim();
    if (!raw) return raw;
    if (/\\\(|\\\)|\\\[|\\\]|\$/.test(raw)) return raw;
    if (/\\[A-Za-z]+/.test(raw) || /\^\{?[^}\s]+\}?/.test(raw)) return '\\(' + raw + '\\)';
    return raw;
  }
  function copyRawText(btn, text) {
    if (typeof text !== 'string') {
      var payload = btn.parentElement ? btn.parentElement.querySelector('.copy-payload') : null;
      text = payload ? payload.value : '';
    }
    if (!text) return;
    function flash() {
      var orig = btn.innerHTML;
      btn.innerHTML = '&#10003;';
      btn.classList.add('copied');
      setTimeout(function(){ btn.innerHTML = orig; btn.classList.remove('copied'); }, 2000);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(flash).catch(function(){ fallbackCopy(text); flash(); });
    } else { fallbackCopy(text); flash(); }
  }
  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text; ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
    document.body.appendChild(ta); ta.select(); document.execCommand('copy');
    document.body.removeChild(ta);
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
    .brand-bar { display:flex; align-items:center; gap:14px; margin-bottom:16px; }
    .brand-mark {
      width:56px; height:56px; flex:0 0 56px; border-radius:16px; overflow:hidden;
      box-shadow:0 10px 24px rgba(78,55,32,.12);
    }
    .brand-mark svg { display:block; width:100%; height:100%; }
    .brand-eyebrow {
      display:inline-block; font-size:.76rem; letter-spacing:.14em; text-transform:uppercase;
      color:var(--muted); font-family:system-ui,sans-serif; font-weight:700; margin-bottom:4px;
    }
    .brand-title { margin:0; font-size:1.5rem; line-height:1.08; color:var(--ink); }
    .site-nav { display:flex; flex-wrap:wrap; gap:8px; margin:0 0 18px; }
    .nav-pill {
      display:inline-flex; align-items:center; justify-content:center;
      padding:8px 14px; border-radius:999px; border:1px solid var(--line);
      background:rgba(255,255,255,.72); color:var(--ink);
      text-decoration:none; font-family:system-ui,sans-serif; font-size:.88rem; font-weight:700;
    }
    .nav-pill.active { background:#e2e8f0; color:#334155; }
    .header-subtitle {
      margin:0 0 14px;
      color:var(--muted);
      font-family:system-ui,sans-serif;
      font-size:.96rem;
      line-height:1.55;
    }
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
    .btn-delete { color:#dc2626; border-color:#fca5a5; }
    .btn-delete:hover { background:#dc2626; color:#fff; border-color:#dc2626; }
    .copy-btn {
      appearance:none; border:1px solid var(--line); background:rgba(255,255,255,.7);
      color:var(--muted); border-radius:6px; cursor:pointer;
      padding:3px 7px; font-size:.85rem;
      white-space:nowrap; transition:all .15s;
      display:inline-flex; align-items:center; flex-shrink:0; margin-left:10px;
    }
    .copy-btn:hover { border-color:var(--accent); color:var(--accent); }
    .copy-btn.copied { border-color:var(--correct); color:var(--correct); background:var(--correct-bg); }

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
    .q-tools { display:flex; align-items:center; gap:10px; flex-wrap:wrap; max-width:100%; }
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

    @media (max-width: 720px) {
      .page { width:min(860px,calc(100vw - 24px)); margin:20px auto 48px; }
      .header-card, .q-card { padding:20px 18px; }
      .brand-bar { align-items:flex-start; }
      .header-card h1 { font-size:1.55rem; }
      .meta { gap:8px; }
      .actions .btn { flex:1 1 220px; text-align:center; }
      .q-text { font-size:1rem; line-height:1.7; }
      .mcq-result-opt { padding:10px 12px; }
      .q-tools { width:100%; justify-content:space-between; }
      .q-source { max-width:100%; overflow-wrap:anywhere; }
    }

    @media (max-width: 520px) {
      .header-card, .q-card { border-radius:16px; }
      .brand-mark { width:48px; height:48px; flex-basis:48px; }
      .brand-title { font-size:1.3rem; }
      .nav-pill, .actions .btn { width:100%; }
      .actions { align-items:stretch; }
      .q-header { gap:12px; }
      .q-tools { align-items:flex-start; }
      .copy-btn { margin-left:0; }
    }

    @media print {
      body { background:#fff; }
      .actions, .btn { display:none !important; }
      .page { width:100%; margin:0; }
      .header-card, .q-card { box-shadow:none; border:1px solid #ccc; }
    }
    html.experience-staging {
      --stage-ink: #10233b;
      --stage-orange-500: #f97316;
      --stage-success: #15803d;
      --stage-success-bg: #dcfce7;
      --stage-amber: #d97706;
      --stage-amber-bg: #fef3c7;
    }
    html.experience-staging body {
      font-family: "Inter", "Segoe UI", sans-serif;
      color: var(--stage-ink);
      background:
        radial-gradient(circle at top left, rgba(249, 115, 22, 0.08), transparent 24%),
        radial-gradient(circle at top right, rgba(29, 78, 216, 0.08), transparent 26%),
        linear-gradient(180deg, #f8fafc 0%, #eef4fb 100%);
    }
    html.experience-staging .header-card,
    html.experience-staging .q-card {
      border-radius: 24px;
      border-color: rgba(148, 163, 184, 0.24);
      box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
      background: rgba(255,255,255,0.94);
    }
    html.experience-staging .nav-pill {
      background: #fff;
      border-color: rgba(148, 163, 184, 0.28);
      color: var(--stage-ink);
    }
    html.experience-staging .nav-pill.active {
      background: #dbeafe;
      color: #1e3a8a;
      border-color: rgba(29, 78, 216, 0.24);
    }
    html.experience-staging .header-subtitle {
      color: #516173;
    }
    html.experience-staging .partial-banner,
    html.experience-staging .chip-progress,
    html.experience-staging .chip-score-partial,
    html.experience-staging .chip-time,
    html.experience-staging .badge-current {
      background: var(--stage-amber-bg);
      color: var(--stage-amber);
    }
    html.experience-staging .chip-score-perfect {
      background: var(--stage-success-bg);
      color: var(--stage-success);
    }
    html.experience-staging .badge-wrong,
    html.experience-staging .mcq-result-opt.opt-wrong {
      background: var(--stage-amber-bg);
      color: var(--stage-amber);
      border-color: var(--stage-amber);
    }
    html.experience-staging .mcq-result-opt.opt-wrong .opt-letter {
      color: var(--stage-amber);
    }
  </style>
</head>
<body>
<div class="page">
  <div class="header-card">
    <div class="brand-bar">
      <div class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 72 72" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="partialBrandGlow" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#fff5da"/>
              <stop offset="55%" stop-color="#f3c98f"/>
              <stop offset="100%" stop-color="#cf7c43"/>
            </linearGradient>
          </defs>
          <rect width="72" height="72" rx="16" fill="url(#partialBrandGlow)"/>
          <circle cx="36" cy="36" r="22" fill="none" stroke="#8b4a2c" stroke-width="2.4" opacity="0.35"/>
          <circle cx="36" cy="36" r="14" fill="none" stroke="#8b4a2c" stroke-width="1.7" opacity="0.22"/>
          <path d="M12 43 C21 28, 28 52, 37 37 S53 21, 60 33" fill="none" stroke="#134f59" stroke-width="3.2" stroke-linecap="round"/>
          <circle cx="24" cy="25" r="3.4" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.4"/>
          <circle cx="51" cy="21" r="2.8" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.2"/>
          <text x="36" y="53" text-anchor="middle" font-size="21" font-family="Georgia, serif" font-weight="700" fill="#8b4a2c">π</text>
        </svg>
      </div>
      <div>
        <span class="brand-eyebrow">Math Delight</span>
        <h2 class="brand-title">Algebra II Trig Tutor</h2>
      </div>
    </div>
    <nav class="site-nav" aria-label="Site sections">
      <a class="nav-pill" href="../index.html">Home</a>
      <a class="nav-pill" href="../library.html">Library</a>
      <a class="nav-pill" href="../live-tutor.html">Live Tutor</a>
      <a class="nav-pill" href="index.html">Challenge Exams</a>
      <a class="nav-pill" href="reports.php">Reports</a>
      <span class="nav-pill active">Partial View</span>
    </nav>
    <div class="partial-banner">&#9203; In Progress — Partial View</div>
    <h1><?= $exam_title ?></h1>
    <p class="header-subtitle">This progress snapshot now uses the same top-card structure as the rest of the site experience.</p>
    <div class="meta">
      <span class="chip chip-progress">&#9203; <?= $answered_cnt ?>/<?= $total_q ?> answered &middot; Q<?= $current_question ?></span>
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
      <a class="btn btn-delete" href="admin/delete.php?type=progress&email=<?= urlencode($row['user_email']) ?>&exam_id=<?= urlencode($row['exam_id']) ?>">&#128465; Delete</a>
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
    $source_raw = $item['source_label'] ?? '';
    $source  = htmlspecialchars($source_raw);
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

    $copy_lines = [$qtext, ''];
    foreach ($options as $optStr) { $copy_lines[] = $optStr; }
    if ($ans)     { $copy_lines[] = ''; $copy_lines[] = 'Your answer: ' . $ans . ($is_correct ? ' ✓' : ($is_wrong ? ' ✗' : '')); }
    if ($correct) { $copy_lines[] = 'Correct answer: ' . $correct; }
    $copy_text = implode("\n", $copy_lines);
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
      <span class="q-tools">
        <span class="q-source" id="qs-<?= $qnum ?>" data-raw="<?= $source ?>"></span>
        <textarea class="copy-payload" hidden><?= htmlspecialchars($copy_text) ?></textarea>
        <button class="copy-btn" type="button" onclick="copyRawText(this)">&#128203;</button>
      </span>
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
    var sourceEl = document.getElementById('qs-<?= $qnum ?>');
    qEl.innerHTML = mdToHtml(<?= json_encode($qtext) ?>);
    if (sourceEl && sourceEl.dataset.raw) {
      sourceEl.innerHTML = inlineMdToHtml(normalizeOptionMath(sourceEl.dataset.raw));
      sourceEl.removeAttribute('data-raw');
    }
    <?php if (!empty($options)): ?>
    document.querySelectorAll('#opts-<?= $qnum ?> .opt-text[data-raw]').forEach(function(el){
      el.innerHTML = mdToHtml(normalizeOptionMath(el.dataset.raw));
      el.removeAttribute('data-raw');
    });
    if (window.MathJax && MathJax.typesetPromise) {
      MathJax.typesetPromise([qEl, sourceEl, document.getElementById('opts-<?= $qnum ?>')].filter(Boolean));
    }
    <?php else: ?>
    if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([qEl, sourceEl].filter(Boolean));
    <?php endif; ?>
  })();
  </script>
  <?php endforeach; ?>
</div>

</body>
</html>
