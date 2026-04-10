<?php
header('Content-Type: application/json');
$email = $_SERVER['HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL'] ?? '';
echo json_encode(['email' => $email ?: null]);
