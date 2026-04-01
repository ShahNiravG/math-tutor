<?php
require_once __DIR__ . '/config.php';

try {
    $pdo = new PDO(
        'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
        DB_USER, DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    $stmt = $pdo->query(
        "SELECT token, exam_id, exam_title, answers_json, time_seconds, user_email, submitted_at
         FROM challenge_results
         ORDER BY submitted_at DESC"
    );
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    http_response_code(500);
    die('<h1>Database error: ' . htmlspecialchars($e->getMessage()) . '</h1>');
}

// Also fetch in-progress exams
$progress_rows = [];
try {
    $prog = $pdo->query(
        "SELECT exam_id, exam_title, answered_count, current_idx, timer_secs, user_email, last_saved_at
         FROM challenge_progress
         ORDER BY last_saved_at DESC"
    );
    $progress_rows = $prog->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) { /* table may not exist yet if no exam has been started */ }

// Build per-user submission lists with scores
$by_user = [];
foreach ($rows as $row) {
    $answers = json_decode($row['answers_json'], true) ?: [];
    $score = 0;
    foreach ($answers as $item) {
        if (!empty($item['answer']) && !empty($item['correct']) && $item['answer'] === $item['correct']) {
            $score++;
        }
    }
    $email = $row['user_email'] ?: 'anonymous';
    if (!isset($by_user[$email])) {
        $by_user[$email] = ['submissions' => [], 'in_progress' => [], 'perfect' => 0];
    }
    $is_perfect = ($score === count($answers) && count($answers) > 0);
    if ($is_perfect) $by_user[$email]['perfect']++;
    $by_user[$email]['submissions'][] = [
        'token'        => $row['token'],
        'exam_id'      => $row['exam_id'],
        'exam_title'   => htmlspecialchars($row['exam_title']),
        'score'        => $score,
        'total'        => count($answers),
        'time_secs'    => (int)$row['time_seconds'],
        'submitted_at' => htmlspecialchars($row['submitted_at']),
    ];
}

// Merge in-progress entries (keyed by user_email)
foreach ($progress_rows as $p) {
    $email = $p['user_email'] ?: 'anonymous';
    if (!isset($by_user[$email])) {
        $by_user[$email] = ['submissions' => [], 'in_progress' => [], 'perfect' => 0];
    }
    $by_user[$email]['in_progress'][] = [
        'exam_id'       => $p['exam_id'],
        'exam_title'    => htmlspecialchars($p['exam_title']),
        'answered'      => (int)$p['answered_count'],
        'current_idx'   => (int)$p['current_idx'],
        'timer_secs'    => (int)$p['timer_secs'],
        'last_saved_at' => htmlspecialchars($p['last_saved_at']),
    ];
}

$users = array_keys($by_user);
$total_submissions = 0;
foreach ($by_user as $u) { $total_submissions += count($u['submissions']); }
$total_in_progress = 0;
foreach ($by_user as $u) { $total_in_progress += count($u['in_progress']); }
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Challenge Reports</title>
  <style>
    :root {
      --bg: #f5f1e8; --paper: #fffaf2; --ink: #1f2a33; --muted: #5b6a74;
      --accent: #a14d2e; --accent-soft: #ead2c5; --line: #d8cfc2;
      --teal: #134f59; --teal-light: #e0f2f5;
      --correct: #166534; --correct-bg: #dcfce7;
      --wrong: #dc2626; --wrong-bg: #fee2e2;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f6efe3 0%, var(--bg) 100%);
      min-height: 100vh;
    }
    .page { width: min(960px, calc(100vw - 32px)); margin: 32px auto 80px; }

    /* ── Header card ── */
    .header-card {
      background: rgba(255,250,242,.92); border: 1px solid var(--line);
      border-radius: 18px; padding: 26px 32px 28px; margin-bottom: 28px;
      box-shadow: 0 8px 24px rgba(78,55,32,.07);
    }
    .brand-bar { display: flex; align-items: center; gap: 14px; margin-bottom: 16px; }
    .brand-mark {
      width: 52px; height: 52px; flex: 0 0 52px;
      border-radius: 14px; overflow: hidden;
      box-shadow: 0 6px 18px rgba(78,55,32,.12);
    }
    .brand-mark svg { display: block; width: 100%; height: 100%; }
    .brand-eyebrow {
      display: block; font-size: .75rem; letter-spacing: .14em;
      text-transform: uppercase; color: var(--muted);
      font-family: system-ui,sans-serif; font-weight: 700; margin-bottom: 3px;
    }
    .brand-title { margin: 0; font-size: 1.5rem; line-height: 1.1; }
    .site-nav { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
    .nav-pill {
      display: inline-flex; align-items: center; padding: 8px 14px;
      border-radius: 999px; border: 1px solid var(--line);
      background: rgba(255,255,255,.72); color: var(--ink);
      text-decoration: none; font-family: system-ui,sans-serif;
      font-size: .88rem; font-weight: 700;
    }
    .nav-pill.active { background: var(--accent-soft); border-color: #cabaa4; color: #6a2e16; }
    .nav-pill:hover { border-color: var(--accent); }
    .auth-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.2rem;
      height: 1.2rem;
      margin-right: 7px;
      border-radius: 999px;
      background: #8b4a2c;
      color: #fff7f0;
      font-size: .82rem;
      font-weight: 700;
      line-height: 1;
      box-shadow: inset 0 -1px 0 rgba(0,0,0,.16);
    }
    .page-heading { margin: 4px 0 6px; font-size: 1.9rem; color: var(--teal); }
    .page-sub { margin: 0; color: var(--muted); font-size: .95rem; font-family: system-ui,sans-serif; }
    .summary-row { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
    .chip {
      display: inline-block; padding: 5px 14px; border-radius: 999px;
      font-size: .85rem; font-weight: 600; font-family: system-ui,sans-serif;
    }
    .chip-neutral { background: #e2e8f0; color: #334155; }
    .chip-teal    { background: var(--teal-light); color: var(--teal); }
    .chip-amber   { background: #fef9c3; color: #854d0e; }

    /* ── User picker cards ── */
    .user-picker {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }
    .user-card {
      background: var(--paper); border: 2px solid var(--line);
      border-radius: 18px; padding: 22px 22px 20px;
      cursor: pointer; transition: border-color .15s, box-shadow .15s, transform .1s;
      box-shadow: 0 4px 14px rgba(78,55,32,.06);
      display: flex; flex-direction: column; gap: 10px;
      text-align: left;
    }
    .user-card:hover {
      border-color: var(--teal); box-shadow: 0 6px 20px rgba(19,79,89,.12);
      transform: translateY(-2px);
    }
    .user-card.selected {
      border-color: var(--teal); background: var(--teal-light);
      box-shadow: 0 6px 20px rgba(19,79,89,.15);
    }
    .user-card-top { display: flex; align-items: center; gap: 12px; }
    .user-avatar {
      width: 44px; height: 44px; border-radius: 50%;
      background: var(--teal); color: #fff;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.15rem; font-weight: 700;
      font-family: system-ui,sans-serif; flex-shrink: 0;
    }
    .user-card.selected .user-avatar { background: var(--teal); }
    .user-card-name {
      font-size: .95rem; font-weight: 700;
      word-break: break-all; line-height: 1.25;
      font-family: system-ui,sans-serif;
    }
    .user-card-stats { display: flex; flex-wrap: wrap; gap: 8px; }
    .stat-pill {
      display: inline-block; padding: 3px 10px; border-radius: 999px;
      font-size: .78rem; font-weight: 600; font-family: system-ui,sans-serif;
    }
    .stat-exams    { background: #e2e8f0; color: #334155; }
    .stat-perfect  { background: var(--correct-bg); color: var(--correct); }
    .stat-avg      { background: #fef9c3; color: #854d0e; }
    .stat-progress { background: #fef9c3; color: #92400e; }

    /* ── In-progress rows ── */
    tr.row-progress { background: #fffbeb; }
    tr.row-progress:hover { background: #fef3c7; }
    tr.row-progress td { border-left: 3px solid #f59e0b; }
    tr.row-progress td:not(:first-child) { border-left: none; }
    .badge-progress {
      display: inline-block; padding: 3px 11px; border-radius: 999px;
      font-size: .78rem; font-weight: 700; font-family: system-ui,sans-serif;
      background: #fef9c3; color: #92400e;
    }
    .section-label {
      font-size: .78rem; font-family: system-ui,sans-serif; font-weight: 700;
      letter-spacing: .07em; text-transform: uppercase; color: var(--muted);
      padding: 10px 16px 6px; background: #f3ede2;
      border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
    }
    .section-label:first-child { border-top: none; }

    /* ── Exam table ── */
    .exam-panel { display: none; }
    .exam-panel.active { display: block; }
    .panel-header {
      display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
      margin-bottom: 12px;
    }
    .panel-title { font-size: 1.2rem; font-weight: 700; margin: 0; }
    .panel-email { font-size: .88rem; color: var(--muted); font-family: system-ui,sans-serif; }

    .table-wrap {
      background: var(--paper); border: 1px solid var(--line);
      border-radius: 14px; overflow: hidden;
      box-shadow: 0 4px 14px rgba(78,55,32,.06);
    }
    table { width: 100%; border-collapse: collapse; font-size: .92rem; }
    thead th {
      background: #f3ede2; padding: 10px 16px; text-align: left;
      font-family: system-ui,sans-serif; font-size: .75rem; font-weight: 700;
      letter-spacing: .07em; text-transform: uppercase;
      color: var(--muted); border-bottom: 1px solid var(--line);
    }
    tbody tr { border-bottom: 1px solid var(--line); transition: background .1s; }
    tbody tr:last-child { border-bottom: none; }
    tbody tr:hover { background: #fdf7ee; }
    td { padding: 12px 16px; vertical-align: middle; }
    .td-title { font-weight: 600; }
    .td-date, .td-time {
      font-family: system-ui,sans-serif; font-size: .85rem;
      color: var(--muted); white-space: nowrap;
    }
    .score-chip {
      display: inline-block; padding: 3px 11px; border-radius: 999px;
      font-size: .82rem; font-weight: 700; font-family: system-ui,sans-serif;
    }
    .score-perfect { background: var(--correct-bg); color: var(--correct); }
    .score-partial  { background: #fef9c3; color: #854d0e; }
    .score-low      { background: var(--wrong-bg); color: var(--wrong); }
    .view-btn {
      display: inline-block; padding: 6px 14px; border-radius: 999px;
      border: 1px solid var(--line); background: #fff; color: var(--accent);
      text-decoration: none; font-family: system-ui,sans-serif;
      font-size: .82rem; font-weight: 700; white-space: nowrap;
      transition: background .12s, color .12s;
    }
    .view-btn:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

    .empty-state {
      text-align: center; color: var(--muted);
      padding: 48px 24px; font-family: system-ui,sans-serif;
    }

    @media (max-width: 600px) {
      .th-time, .td-time { display: none; }
    }
  </style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div class="header-card">
    <div class="brand-bar">
      <div class="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 72 72" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="rptGlow" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#fff5da"/>
              <stop offset="55%" stop-color="#f3c98f"/>
              <stop offset="100%" stop-color="#cf7c43"/>
            </linearGradient>
          </defs>
          <rect width="72" height="72" rx="16" fill="url(#rptGlow)"/>
          <circle cx="36" cy="36" r="22" fill="none" stroke="#8b4a2c" stroke-width="2.4" opacity="0.35"/>
          <circle cx="36" cy="36" r="14" fill="none" stroke="#8b4a2c" stroke-width="1.7" opacity="0.22"/>
          <path d="M12 43 C21 28, 28 52, 37 37 S53 21, 60 33" fill="none" stroke="#134f59" stroke-width="3.2" stroke-linecap="round"/>
          <circle cx="24" cy="25" r="3.4" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.4"/>
          <circle cx="51" cy="21" r="2.8" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.2"/>
          <text x="36" y="53" text-anchor="middle" font-size="21" font-family="Georgia,serif" font-weight="700" fill="#8b4a2c">π</text>
        </svg>
      </div>
      <div>
        <span class="brand-eyebrow">Math Delight</span>
        <h1 class="brand-title">Algebra II Trig Tutor</h1>
      </div>
    </div>
    <nav class="site-nav" aria-label="Site sections">
      <a class="nav-pill" href="../index.html">Home</a>
      <a class="nav-pill" href="../library.html">Library</a>
      <a class="nav-pill" href="../live-tutor.html">Live Tutor</a>
      <a class="nav-pill" href="index.html">Challenge Exams</a>
      <a class="nav-pill active" href="reports.php"><span class="auth-icon" aria-hidden="true">&#128737;&#65038;</span>Reports</a>
    </nav>
    <h2 class="page-heading">&#128202; Challenge Reports</h2>
    <p class="page-sub">Select a user to see their submitted exams.</p>
    <div class="summary-row">
      <span class="chip chip-neutral">&#128203; <?= $total_submissions ?> submitted</span>
      <?php if ($total_in_progress > 0): ?>
      <span class="chip chip-amber">&#9203; <?= $total_in_progress ?> in progress</span>
      <?php endif; ?>
      <span class="chip chip-teal">&#128100; <?= count($users) ?> user<?= count($users) !== 1 ? 's' : '' ?></span>
    </div>
  </div>

  <?php if (empty($users)): ?>
  <div class="empty-state">No submissions yet.</div>
  <?php else: ?>

  <!-- User picker -->
  <div class="user-picker" id="user-picker">
    <?php foreach ($users as $idx => $email):
      $u = $by_user[$email];
      $count = count($u['submissions']);
      $prog_count = count($u['in_progress']);
      $perfect = $u['perfect'];
      $total_score = array_sum(array_column($u['submissions'], 'score'));
      $total_q     = array_sum(array_column($u['submissions'], 'total'));
      $avg_pct = $total_q > 0 ? round(($total_score / $total_q) * 100) : 0;
      $initials = strtoupper(substr($email, 0, 1));
      $uid = 'user-' . $idx;
    ?>
    <button class="user-card <?= $idx === 0 ? 'selected' : '' ?>"
            onclick="selectUser('<?= $uid ?>', this)"
            aria-pressed="<?= $idx === 0 ? 'true' : 'false' ?>">
      <div class="user-card-top">
        <div class="user-avatar"><?= htmlspecialchars($initials) ?></div>
        <div class="user-card-name"><?= htmlspecialchars($email) ?></div>
      </div>
      <div class="user-card-stats">
        <span class="stat-pill stat-exams">&#128203; <?= $count ?> submitted</span>
        <?php if ($prog_count > 0): ?>
        <span class="stat-pill stat-progress">&#9203; <?= $prog_count ?> in progress</span>
        <?php endif; ?>
        <?php if ($perfect > 0): ?>
        <span class="stat-pill stat-perfect">&#127942; <?= $perfect ?> perfect</span>
        <?php endif; ?>
        <?php if ($count > 0): ?>
        <span class="stat-pill stat-avg">&#128200; <?= $avg_pct ?>% avg</span>
        <?php endif; ?>
      </div>
    </button>
    <?php endforeach; ?>
  </div>

  <!-- Per-user exam panels -->
  <?php foreach ($users as $idx => $email):
    $u = $by_user[$email];
    $uid = 'user-' . $idx;
    $has_submitted  = count($u['submissions']) > 0;
    $has_in_progress = count($u['in_progress']) > 0;
  ?>
  <div class="exam-panel <?= $idx === 0 ? 'active' : '' ?>" id="<?= $uid ?>">
    <div class="panel-header">
      <p class="panel-title">&#128100; <?= htmlspecialchars($email) ?></p>
      <span class="panel-email">
        <?= count($u['submissions']) ?> submitted<?= $has_in_progress ? ', ' . count($u['in_progress']) . ' in progress' : '' ?>
      </span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Exam</th>
            <th>Score / Progress</th>
            <th class="th-time">Time</th>
            <th>Date</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <?php if ($has_in_progress): ?>
          <tr><td colspan="5" class="section-label">&#9203; In Progress</td></tr>
          <?php foreach ($u['in_progress'] as $p):
            $m = intdiv($p['timer_secs'], 60);
            $sec = $p['timer_secs'] % 60;
            $time_fmt = sprintf('%d:%02d', $m, $sec);
          ?>
          <tr class="row-progress">
            <td class="td-title"><?= $p['exam_title'] ?></td>
            <td><span class="badge-progress">&#9203; <?= $p['answered'] ?>/10 answered &middot; Q<?= $p['current_idx'] + 1 ?></span></td>
            <td class="td-time">&#9201; <?= $time_fmt ?></td>
            <td class="td-date"><?= $p['last_saved_at'] ?></td>
            <td></td>
          </tr>
          <?php endforeach; ?>
          <?php endif; ?>

          <?php if ($has_submitted): ?>
          <?php if ($has_in_progress): ?>
          <tr><td colspan="5" class="section-label">&#128203; Submitted</td></tr>
          <?php endif; ?>
          <?php foreach ($u['submissions'] as $s):
            $pct = $s['total'] > 0 ? $s['score'] / $s['total'] : 0;
            $cls = $pct >= 1.0 ? 'score-perfect' : ($pct >= 0.6 ? 'score-partial' : 'score-low');
            $icon = $pct >= 1.0 ? '&#127942;' : ($pct >= 0.6 ? '&#128993;' : '&#128308;');
            $m = intdiv($s['time_secs'], 60);
            $sec = $s['time_secs'] % 60;
            $time_fmt = sprintf('%d:%02d', $m, $sec);
          ?>
          <tr>
            <td class="td-title"><?= $s['exam_title'] ?></td>
            <td><span class="score-chip <?= $cls ?>"><?= $icon ?> <?= $s['score'] ?>/<?= $s['total'] ?></span></td>
            <td class="td-time">&#9201; <?= $time_fmt ?></td>
            <td class="td-date"><?= $s['submitted_at'] ?></td>
            <td><a class="view-btn" href="result.php?token=<?= htmlspecialchars($s['token']) ?>">View Result &rarr;</a></td>
          </tr>
          <?php endforeach; ?>
          <?php endif; ?>
        </tbody>
      </table>
    </div>
  </div>
  <?php endforeach; ?>

  <?php endif; ?>
</div>

<script>
function selectUser(uid, btn) {
  // Deselect all cards
  document.querySelectorAll('.user-card').forEach(function(c) {
    c.classList.remove('selected');
    c.setAttribute('aria-pressed', 'false');
  });
  // Hide all panels
  document.querySelectorAll('.exam-panel').forEach(function(p) {
    p.classList.remove('active');
  });
  // Activate selected
  btn.classList.add('selected');
  btn.setAttribute('aria-pressed', 'true');
  document.getElementById(uid).classList.add('active');
}
</script>
</body>
</html>
