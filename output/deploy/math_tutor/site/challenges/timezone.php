<?php

const CHALLENGE_CALIFORNIA_TZ = 'America/Los_Angeles';

function challenge_source_timezone(): DateTimeZone {
    static $tz = null;
    if ($tz === null) {
        try {
            $tz = new DateTimeZone(date_default_timezone_get());
        } catch (Exception $e) {
            $tz = new DateTimeZone('UTC');
        }
    }
    return $tz;
}

function challenge_california_timezone(): DateTimeZone {
    static $tz = null;
    if ($tz === null) {
        $tz = new DateTimeZone(CHALLENGE_CALIFORNIA_TZ);
    }
    return $tz;
}

function challenge_now_storage(): string {
    return (new DateTimeImmutable('now', challenge_source_timezone()))->format('Y-m-d H:i:s');
}

function challenge_format_california_timestamp(?string $raw): string {
    $value = trim((string)$raw);
    if ($value === '') {
        return '';
    }

    try {
        $dt = new DateTimeImmutable($value, challenge_source_timezone());
    } catch (Exception $e) {
        return $value;
    }

    return $dt
        ->setTimezone(challenge_california_timezone())
        ->format('M j, Y g:i A T');
}
