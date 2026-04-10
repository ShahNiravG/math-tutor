<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/timezone.php';
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
if (!$input || !isset($input['exam_id'], $input['exam_title'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid input']);
    exit;
}

$exam_id       = substr(preg_replace('/[^a-z0-9-]/', '', $input['exam_id']), 0, 32);
$exam_title    = substr($input['exam_title'], 0, 64);
$answered      = max(0, (int)($input['answered_count'] ?? 0));
$current_idx   = max(0, (int)($input['current_idx']   ?? 0));
$timer_secs    = max(0, (int)($input['timer_secs']     ?? 0));
$answers_json  = isset($input['answers']) ? json_encode($input['answers']) : null;
$user_email    = substr($_SERVER['HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL'] ?? '', 0, 255);
$saved_at      = challenge_now_storage();

if (!$user_email) {
    // No authenticated user — nothing to save server-side
    echo json_encode(['ok' => true]);
    exit;
}

try {
    $pdo = new PDO(
        'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
        DB_USER, DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );

    $pdo->exec("CREATE TABLE IF NOT EXISTS challenge_progress (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        exam_id        VARCHAR(32)  NOT NULL,
        exam_title     VARCHAR(64)  NOT NULL,
        answered_count INT          NOT NULL DEFAULT 0,
        current_idx    INT          NOT NULL DEFAULT 0,
        timer_secs     INT          NOT NULL DEFAULT 0,
        answers_json   MEDIUMTEXT   DEFAULT NULL,
        user_email     VARCHAR(255) NOT NULL,
        last_saved_at  DATETIME     NOT NULL,
        UNIQUE KEY uniq_user_exam (user_email, exam_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

    // Add answers_json column if upgrading from old schema
    try {
        $pdo->exec("ALTER TABLE challenge_progress ADD COLUMN answers_json MEDIUMTEXT DEFAULT NULL");
    } catch (PDOException $e) { /* column already exists */ }

    $pdo->prepare(
        "INSERT INTO challenge_progress
             (exam_id, exam_title, answered_count, current_idx, timer_secs, answers_json, user_email, last_saved_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
         ON DUPLICATE KEY UPDATE
             exam_title     = VALUES(exam_title),
             answered_count = VALUES(answered_count),
             current_idx    = VALUES(current_idx),
             timer_secs     = VALUES(timer_secs),
             answers_json   = COALESCE(VALUES(answers_json), answers_json),
             last_saved_at  = VALUES(last_saved_at)"
    )->execute([$exam_id, $exam_title, $answered, $current_idx, $timer_secs, $answers_json, $user_email, $saved_at]);

    echo json_encode(['ok' => true]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error: ' . $e->getMessage()]);
}
