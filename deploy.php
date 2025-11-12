<?php
// --- CONFIG ---
$secret = 'SiaSina535';  
$repoPath = '/home/botcynococo/PardisPanel/public'; 
$branch = 'main';

// --- VERIFY SECRET ---
$payload = file_get_contents('php://input');
$headers = getallheaders();
$signature = $headers['X-Hub-Signature-256'] ?? '';
$expected = 'sha256=' . hash_hmac('sha256', $payload, $secret);
if (!hash_equals($expected, $signature)) {
    http_response_code(403);
    exit('Invalid signature');
}

// --- DEPLOY ---
exec("cd $repoPath && git fetch origin $branch && git reset --hard origin/$branch 2>&1", $output);
echo "<pre>";
print_r($output);
echo "</pre>";
?>
