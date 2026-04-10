<?php
require_once __DIR__ . '/config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');

$exam_id = substr(preg_replace('/[^a-z0-9-]/', '', $_GET['exam_id'] ?? ''), 0, 32);
$user_email = substr($_SERVER['HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL'] ?? '', 0, 255);

if (!$exam_id || !$user_email) {
    echo json_encode(['progress' => null]);
    exit;
}

try {
    $pdo = new PDO(
        'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
        DB_USER, DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    $stmt = $pdo->prepare(
        "SELECT exam_id, exam_title, answered_count, current_idx, timer_secs, answers_json, last_saved_at
         FROM challenge_progress
         WHERE user_email = ? AND exam_id = ?
         LIMIT 1"
    );
    $stmt->execute([$user_email, $exam_id]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    if (!$row) {
        echo json_encode(['progress' => null]);
        exit;
    }
    $row['answered_count'] = (int)$row['answered_count'];
    $row['current_idx'] = (int)$row['current_idx'];
    $row['timer_secs'] = (int)$row['timer_secs'];
    $row['answers'] = json_decode($row['answers_json'] ?? 'null', true) ?: [];
    unset($row['answers_json']);
    echo json_encode(['progress' => $row]);
} catch (PDOException $e) {
    echo json_encode(['progress' => null]);
}
