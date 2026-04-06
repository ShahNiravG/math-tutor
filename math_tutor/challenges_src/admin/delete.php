<?php
require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../timezone.php';

// This endpoint is under challenges/admin/* — restrict to nirav.shah@gmail.com
// via a Cloudflare Access policy on the /challenges/admin/* path.
// As a defence-in-depth check we also verify the header here.
$admin_email = 'nirav.shah@gmail.com';
$caller = $_SERVER['HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL'] ?? '';
if ($caller !== $admin_email) {
    http_response_code(403);
    die('<h1>403 Forbidden</h1><p>Admin access only.</p>');
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function db(): PDO {
    $pdo = new PDO(
        'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
        DB_USER, DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    return $pdo;
}

function esc(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}

// ── Route ────────────────────────────────────────────────────────────────────

$type = $_GET['type'] ?? $_POST['type'] ?? '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // CSRF check: require the hidden _confirm field to equal "yes"
    if (($_POST['_confirm'] ?? '') !== 'yes') {
        http_response_code(400);
        die('<h1>Bad request</h1>');
    }

    try {
        $pdo = db();
        if ($type === 'result') {
            $token = preg_replace('/[^a-f0-9]/', '', $_POST['token'] ?? '');
            if (strlen($token) !== 12) { http_response_code(400); die('<h1>Invalid token</h1>'); }
            $pdo->prepare("DELETE FROM challenge_results WHERE token = ?")->execute([$token]);
        } elseif ($type === 'progress') {
            $email   = $_POST['email']   ?? '';
            $exam_id = substr(preg_replace('/[^a-z0-9-]/', '', $_POST['exam_id'] ?? ''), 0, 32);
            if (!$email || !$exam_id) { http_response_code(400); die('<h1>Missing fields</h1>'); }
            $pdo->prepare("DELETE FROM challenge_progress WHERE user_email = ? AND exam_id = ?")->execute([$email, $exam_id]);
        } else {
            http_response_code(400);
            die('<h1>Unknown type</h1>');
        }
    } catch (PDOException $e) {
        http_response_code(500);
        die('<h1>Database error: ' . esc($e->getMessage()) . '</h1>');
    }

    // Redirect back to reports after deletion
    header('Location: ../reports.php');
    exit;
}

// ── GET: show confirmation page ───────────────────────────────────────────────

// Fetch the record so we can show details
$record = null;
$error  = null;

try {
    $pdo = db();
    if ($type === 'result') {
        $token = preg_replace('/[^a-f0-9]/', '', $_GET['token'] ?? '');
        if (strlen($token) !== 12) { http_response_code(400); die('<h1>Invalid token</h1>'); }
        $stmt = $pdo->prepare("SELECT token, exam_title, user_email, submitted_at FROM challenge_results WHERE token = ?");
        $stmt->execute([$token]);
        $record = $stmt->fetch(PDO::FETCH_ASSOC);
    } elseif ($type === 'progress') {
        $email   = $_GET['email']   ?? '';
        $exam_id = substr(preg_replace('/[^a-z0-9-]/', '', $_GET['exam_id'] ?? ''), 0, 32);
        $stmt = $pdo->prepare("SELECT exam_id, exam_title, user_email, last_saved_at, answered_count FROM challenge_progress WHERE user_email = ? AND exam_id = ?");
        $stmt->execute([$email, $exam_id]);
        $record = $stmt->fetch(PDO::FETCH_ASSOC);
    } else {
        http_response_code(400);
        die('<h1>Unknown type</h1>');
    }
} catch (PDOException $e) {
    $error = $e->getMessage();
}

if (!$record && !$error) {
    http_response_code(404);
    die('<h1>Record not found</h1>');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Delete <?= $type === 'result' ? 'Result' : 'In-Progress Exam' ?></title>
  <style>
    :root { --bg:#f5f1e8; --paper:#fffaf2; --ink:#1f2a33; --muted:#5b6a74;
            --accent:#a14d2e; --line:#d8cfc2; --wrong:#dc2626; --wrong-bg:#fee2e2; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Georgia,"Times New Roman",serif; color:var(--ink);
           background:linear-gradient(180deg,#f6efe3 0%,var(--bg) 100%); min-height:100vh;
           display:flex; align-items:center; justify-content:center; }
    .card { background:var(--paper); border:1px solid var(--line); border-radius:18px;
            padding:36px 40px; max-width:480px; width:calc(100vw - 32px);
            box-shadow:0 8px 24px rgba(78,55,32,.1); }
    .danger-icon { font-size:2.4rem; margin-bottom:12px; }
    h1 { margin:0 0 8px; font-size:1.5rem; color:var(--wrong); }
    .desc { color:var(--muted); font-size:.95rem; margin:0 0 20px; font-family:system-ui,sans-serif; line-height:1.6; }
    .detail-table { width:100%; border-collapse:collapse; margin-bottom:24px; font-size:.9rem; }
    .detail-table td { padding:7px 0; vertical-align:top; }
    .detail-table td:first-child { color:var(--muted); font-family:system-ui,sans-serif;
                                   font-size:.8rem; font-weight:700; text-transform:uppercase;
                                   letter-spacing:.06em; width:120px; padding-right:12px; }
    .actions { display:flex; gap:12px; flex-wrap:wrap; }
    .btn { appearance:none; padding:10px 22px; border-radius:999px; font:inherit;
           font-weight:700; font-size:.95rem; cursor:pointer; border:1px solid var(--line);
           text-decoration:none; display:inline-block; }
    .btn-danger { background:var(--wrong); color:#fff; border-color:var(--wrong); }
    .btn-danger:hover { background:#b91c1c; }
    .btn-cancel { background:#fff; color:var(--accent); }
    .btn-cancel:hover { background:var(--accent); color:#fff; border-color:var(--accent); }
    .warning-box { background:var(--wrong-bg); border:1px solid #fca5a5; border-radius:10px;
                   padding:12px 16px; margin-bottom:20px; font-family:system-ui,sans-serif;
                   font-size:.88rem; color:var(--wrong); }
  </style>
</head>
<body>
<div class="card">
  <div class="danger-icon">&#128465;</div>
  <h1>Delete <?= $type === 'result' ? 'Submitted Result' : 'In-Progress Exam' ?></h1>
  <p class="desc">This will permanently remove the record from the database. This cannot be undone.</p>

  <?php if ($error): ?>
  <div class="warning-box">Database error: <?= esc($error) ?></div>
  <?php else: ?>

  <table class="detail-table">
    <?php if ($type === 'result'): ?>
    <tr><td>Exam</td><td><?= esc($record['exam_title']) ?></td></tr>
    <tr><td>User</td><td><?= esc($record['user_email'] ?: 'anonymous') ?></td></tr>
    <tr><td>Submitted</td><td><?= esc(challenge_format_california_timestamp($record['submitted_at'])) ?></td></tr>
    <tr><td>Token</td><td><code><?= esc($record['token']) ?></code></td></tr>
    <?php else: ?>
    <tr><td>Exam</td><td><?= esc($record['exam_title']) ?></td></tr>
    <tr><td>User</td><td><?= esc($record['user_email']) ?></td></tr>
    <tr><td>Last saved</td><td><?= esc(challenge_format_california_timestamp($record['last_saved_at'])) ?></td></tr>
    <tr><td>Answered</td><td><?= (int)$record['answered_count'] ?>/10</td></tr>
    <?php endif; ?>
  </table>

  <div class="warning-box">&#9888; This action is irreversible.</div>

  <form method="POST" action="delete.php">
    <input type="hidden" name="type" value="<?= esc($type) ?>">
    <input type="hidden" name="_confirm" value="yes">
    <?php if ($type === 'result'): ?>
    <input type="hidden" name="token" value="<?= esc($record['token']) ?>">
    <?php else: ?>
    <input type="hidden" name="email"   value="<?= esc($record['user_email']) ?>">
    <input type="hidden" name="exam_id" value="<?= esc($record['exam_id']) ?>">
    <?php endif; ?>
    <div class="actions">
      <button type="submit" class="btn btn-danger">&#128465; Yes, delete</button>
      <a class="btn btn-cancel" href="../reports.php">Cancel</a>
    </div>
  </form>

  <?php endif; ?>
</div>
</body>
</html>
