drop table if exists d3_block;
create table d3_block (
    gist_id text primary key,
    block_url text,
    fullpage_base64 text,
    block_base64 text,
    block_size int[],
    error text
);
