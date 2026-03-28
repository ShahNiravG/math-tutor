<?php
require_once __DIR__ . '/config.php';
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
$answers     = json_encode($input['answers']);
$time_secs   = max(0, (int)$input['time_seconds']);
$token       = bin2hex(random_bytes(6)); // 12-char hex
$user_email  = substr($_SERVER['HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL'] ?? '', 0, 255);

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
        user_email   VARCHAR(255) DEFAULT NULL,
        submitted_at DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

    // Add user_email column if upgrading from old schema
    try {
        $pdo->exec("ALTER TABLE challenge_results ADD COLUMN user_email VARCHAR(255) DEFAULT NULL");
    } catch (PDOException $e) { /* column already exists */ }

    $stmt = $pdo->prepare(
        "INSERT INTO challenge_results (token, exam_id, exam_title, answers_json, time_seconds, user_email, submitted_at)
         VALUES (?, ?, ?, ?, ?, ?, NOW())"
    );
    $stmt->execute([$token, $exam_id, $exam_title, $answers, $time_secs, $user_email ?: null]);

    echo json_encode(['token' => $token]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error']);
}
