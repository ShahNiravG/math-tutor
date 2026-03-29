<?php
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    fwrite(STDERR, "This script must be run from the command line.\n");
    exit(1);
}

$defaultEnvPath = dirname(__DIR__, 2) . '/.env';
$envPath = $defaultEnvPath;
$confirmed = false;
$dryRun = false;

foreach (array_slice($argv, 1) as $arg) {
    if ($arg === '--yes') {
        $confirmed = true;
        continue;
    }
    if ($arg === '--dry-run') {
        $dryRun = true;
        continue;
    }
    if (str_starts_with($arg, '--env=')) {
        $envPath = substr($arg, 6);
        continue;
    }
    if ($arg === '--help' || $arg === '-h') {
        fwrite(STDOUT, "Usage: php clear_challenge_results.php [--env=/path/to/.env] [--dry-run] [--yes]\n");
        exit(0);
    }

    fwrite(STDERR, "Unknown option: {$arg}\n");
    exit(1);
}

$env = is_file($envPath) ? loadDotenv($envPath) : [];
$host = envValue('MYSQL_HOST', $env) ?: 'localhost';
$dbName = envValue('DBNAME', $env) ?: '';
$dbUser = envValue('DBUSER', $env) ?: '';
$dbPassword = envValue('DBPASSWORD', $env) ?: '';

if ($dbName === '' || $dbUser === '') {
    fwrite(STDERR, "Missing DBNAME or DBUSER in environment or {$envPath}\n");
    exit(1);
}

try {
    $pdo = new PDO(
        sprintf('mysql:host=%s;dbname=%s;charset=utf8mb4', $host, $dbName),
        $dbUser,
        $dbPassword,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
} catch (PDOException $e) {
    fwrite(STDERR, "Database connection failed: {$e->getMessage()}\n");
    exit(1);
}

try {
    $count = (int) $pdo->query('SELECT COUNT(*) FROM challenge_results')->fetchColumn();
} catch (PDOException $e) {
    fwrite(STDERR, "Could not query challenge_results: {$e->getMessage()}\n");
    exit(1);
}

fwrite(STDOUT, "challenge_results rows: {$count}\n");
fwrite(STDOUT, "Database: {$dbName} @ {$host}\n");

if ($dryRun) {
    fwrite(STDOUT, "Dry run only. No rows deleted.\n");
    exit(0);
}

if (!$confirmed) {
    fwrite(STDERR, "Refusing to delete rows without --yes.\n");
    exit(1);
}

try {
    $pdo->exec('DELETE FROM challenge_results');
    fwrite(STDOUT, "Deleted {$count} row(s) from challenge_results.\n");
} catch (PDOException $e) {
    fwrite(STDERR, "Delete failed: {$e->getMessage()}\n");
    exit(1);
}

function loadDotenv(string $path): array
{
    $values = [];
    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if ($lines === false) {
        return $values;
    }

    foreach ($lines as $rawLine) {
        $line = trim($rawLine);
        if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) {
            continue;
        }

        [$key, $value] = explode('=', $line, 2);
        $key = trim($key);
        $value = trim($value);
        if ($key === '') {
            continue;
        }
        $length = strlen($value);
        if ($length >= 2 && (($value[0] === '"' && $value[$length - 1] === '"') || ($value[0] === "'" && $value[$length - 1] === "'"))) {
            $value = substr($value, 1, -1);
        }
        $values[$key] = $value;
    }

    return $values;
}

function envValue(string $key, array $dotenv): ?string
{
    $value = getenv($key);
    if ($value !== false && $value !== '') {
        return $value;
    }

    return $dotenv[$key] ?? null;
}
