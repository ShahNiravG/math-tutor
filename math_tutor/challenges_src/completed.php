<?php
require_once __DIR__ . '/config.php';
header('Content-Type: application/json');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('Expires: 0');

$user_email = $_SERVER['HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL'] ?? '';
if (!$user_email) {
    echo json_encode(['completed' => []]);
    exit;
}

try {
    $pdo = new PDO(
        'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
        DB_USER, DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
    $stmt = $pdo->prepare(
        "SELECT exam_id FROM challenge_results WHERE user_email = ?"
    );
    $stmt->execute([$user_email]);
    $ids = $stmt->fetchAll(PDO::FETCH_COLUMN, 0);
    echo json_encode(['completed' => array_values($ids)]);
} catch (PDOException $e) {
    // Fail open — don't block the picker if DB is unavailable
    echo json_encode(['completed' => []]);
}
