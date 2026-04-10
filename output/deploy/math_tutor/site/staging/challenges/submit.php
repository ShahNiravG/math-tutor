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
if (!$input || !isset($input['exam_id'], $input['exam_title'], $input['answers'], $input['time_seconds'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid input']);
    exit;
}

$exam_id     = substr(preg_replace('/[^a-z0-9-]/', '', $input['exam_id']), 0, 32);
$exam_title  = substr($input['exam_title'], 0, 64);
$answers_arr = is_array($input['answers']) ? $input['answers'] : [];
$answers     = json_encode($answers_arr);
$time_secs   = max(0, (int)$input['time_seconds']);
$token       = bin2hex(random_bytes(6)); // 12-char hex
$user_email  = substr($_SERVER['HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL'] ?? '', 0, 255);
$saved_at    = challenge_now_storage();
$answered_count = 0;
foreach ($answers_arr as $item) {
    if (!empty($item['answer'])) {
        $answered_count++;
    }
}
$is_complete = ($answered_count === count($answers_arr) && count($answers_arr) > 0) ? 1 : 0;

try {
    $pdo = new PDO(
        'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
        DB_USER, DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );

    $pdo->exec("CREATE TABLE IF NOT EXISTS challenge_results (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        token        CHAR(12) NOT NULL UNIQUE,
        exam_id      VARCHAR(32) NOT NULL,
        exam_title   VARCHAR(64) NOT NULL,
        answers_json MEDIUMTEXT NOT NULL,
        time_seconds INT NOT NULL,
        is_complete  TINYINT(1) NOT NULL DEFAULT 1,
        user_email   VARCHAR(255) DEFAULT NULL,
        submitted_at DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

    // Add user_email column if upgrading from old schema
    try {
        $pdo->exec("ALTER TABLE challenge_results ADD COLUMN user_email VARCHAR(255) DEFAULT NULL");
    } catch (PDOException $e) { /* column already exists */ }
    try {
        $pdo->exec("ALTER TABLE challenge_results ADD COLUMN is_complete TINYINT(1) NOT NULL DEFAULT 1");
    } catch (PDOException $e) { /* column already exists */ }

    if (!$is_complete) {
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
        if ($user_email) {
            $current_idx = 0;
            foreach ($answers_arr as $i => $item) {
                if (empty($item['answer'])) {
                    $current_idx = $i;
                    break;
                }
            }
            $pdo->prepare(
                "INSERT INTO challenge_progress
                     (exam_id, exam_title, answered_count, current_idx, timer_secs, answers_json, user_email, last_saved_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                 ON DUPLICATE KEY UPDATE
                     exam_title     = VALUES(exam_title),
                     answered_count = VALUES(answered_count),
                     current_idx    = VALUES(current_idx),
                     timer_secs     = VALUES(timer_secs),
                     answers_json   = VALUES(answers_json),
                     last_saved_at  = VALUES(last_saved_at)"
            )->execute([$exam_id, $exam_title, $answered_count, $current_idx, $time_secs, $answers, $user_email, $saved_at]);
        }
        echo json_encode([
            'partial' => true,
            'partial_url' => 'partial_result.php?exam_id=' . rawurlencode($exam_id),
        ]);
        exit;
    }

    // Prevent duplicate submission: if this user has already submitted this exam, return the
    // existing token so the client can redirect to the already-saved result.
    if ($user_email) {
        $dup = $pdo->prepare(
            "SELECT token FROM challenge_results WHERE user_email = ? AND exam_id = ? AND is_complete = 1 LIMIT 1"
        );
        $dup->execute([$user_email, $exam_id]);
        $existing = $dup->fetch(PDO::FETCH_ASSOC);
        if ($existing) {
            echo json_encode(['token' => $existing['token'], 'already_submitted' => true]);
            exit;
        }
    }

    $stmt = $pdo->prepare(
        "INSERT INTO challenge_results (token, exam_id, exam_title, answers_json, time_seconds, is_complete, user_email, submitted_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    );
    $stmt->execute([$token, $exam_id, $exam_title, $answers, $time_secs, $is_complete, $user_email ?: null, $saved_at]);

    // Clean up any in-progress record for this user+exam now that it's submitted
    if ($user_email) {
        try {
            $pdo->prepare(
                "DELETE FROM challenge_progress WHERE user_email = ? AND exam_id = ?"
            )->execute([$user_email, $exam_id]);
        } catch (PDOException $e) { /* progress table may not exist yet; safe to ignore */ }
    }

    echo json_encode(['token' => $token]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error: ' . $e->getMessage()]);
}
