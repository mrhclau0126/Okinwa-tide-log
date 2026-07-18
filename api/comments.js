// Vercel serverless function: /api/comments
// Per-day family notes ("家庭留言 / 太太備註"), stored in a dedicated Notion database.
// Reuses the same NOTION_TOKEN (integration) as expenses; uses its own database id.
// One row per day; saving the same day again overwrites that row's Comment.
//
// Required environment variables (set in Vercel Project Settings -> Environment Variables):
//   NOTION_TOKEN                 - your Notion integration's "Internal Integration Secret" (same as expenses)
//   NOTION_COMMENTS_DATABASE_ID  - the Comments database ID (the integration must be shared with it)
//
// Expected Notion database properties (exact names, case-sensitive):
//   Day      (title)      e.g. "Day 1" ... "Day 8"
//   Comment  (rich_text)

const NOTION_VERSION = '2022-06-28';

function notionHeaders() {
  return {
    'Authorization': `Bearer ${process.env.NOTION_TOKEN}`,
    'Notion-Version': NOTION_VERSION,
    'Content-Type': 'application/json',
  };
}

const getTitle = (prop) => (prop?.title || []).map((t) => t.plain_text).join('') || '';
const getRichText = (prop) => (prop?.rich_text || []).map((t) => t.plain_text).join('') || '';

// Notion caps a single rich_text object's content at 2000 chars; split just in case.
function chunkText(s) {
  const str = String(s == null ? '' : s);
  const out = [];
  for (let i = 0; i < str.length; i += 1900) {
    out.push({ text: { content: str.slice(i, i + 1900) } });
  }
  return out; // [] clears the field
}

function pageToComment(page) {
  const p = page.properties || {};
  return { id: page.id, day: getTitle(p.Day), text: getRichText(p.Comment) };
}

async function findPageByDay(dbId, day) {
  const r = await fetch(`https://api.notion.com/v1/databases/${dbId}/query`, {
    method: 'POST',
    headers: notionHeaders(),
    body: JSON.stringify({ filter: { property: 'Day', title: { equals: day } }, page_size: 1 }),
  });
  if (!r.ok) return null;
  const data = await r.json();
  return (data.results && data.results[0]) || null;
}

async function handleGet(req, res) {
  const dbId = process.env.NOTION_COMMENTS_DATABASE_ID;
  const r = await fetch(`https://api.notion.com/v1/databases/${dbId}/query`, {
    method: 'POST',
    headers: notionHeaders(),
    body: JSON.stringify({ page_size: 100 }),
  });
  if (!r.ok) {
    const err = await r.text();
    return res.status(r.status).json({ error: 'notion_query_failed', detail: err });
  }
  const data = await r.json();
  const comments = (data.results || []).map(pageToComment);
  return res.status(200).json({ comments });
}

async function handlePost(req, res) {
  const dbId = process.env.NOTION_COMMENTS_DATABASE_ID;
  const b = req.body || {};
  const day = b.day ? String(b.day) : '';
  if (!day) return res.status(400).json({ error: 'missing_day', detail: 'day is required' });

  const commentProp = { rich_text: chunkText(b.text) };
  const existing = await findPageByDay(dbId, day);

  let r;
  if (existing) {
    r = await fetch(`https://api.notion.com/v1/pages/${existing.id}`, {
      method: 'PATCH',
      headers: notionHeaders(),
      body: JSON.stringify({ properties: { Comment: commentProp } }),
    });
  } else {
    r = await fetch('https://api.notion.com/v1/pages', {
      method: 'POST',
      headers: notionHeaders(),
      body: JSON.stringify({
        parent: { database_id: dbId },
        properties: {
          Day: { title: [{ text: { content: day } }] },
          Comment: commentProp,
        },
      }),
    });
  }

  if (!r.ok) {
    const err = await r.text();
    return res.status(r.status).json({ error: 'notion_save_failed', detail: err });
  }
  const page = await r.json();
  return res.status(200).json({ comment: pageToComment(page) });
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  if (!process.env.NOTION_TOKEN || !process.env.NOTION_COMMENTS_DATABASE_ID) {
    return res.status(500).json({
      error: 'not_configured',
      detail: 'NOTION_TOKEN / NOTION_COMMENTS_DATABASE_ID environment variables are not set on this deployment.',
    });
  }

  try {
    if (req.method === 'GET') return await handleGet(req, res);
    if (req.method === 'POST') return await handlePost(req, res);
    return res.status(405).json({ error: 'method_not_allowed' });
  } catch (e) {
    return res.status(500).json({ error: 'server_error', detail: String(e) });
  }
};
