function load(url) {
  const items = fetchAll(url);
  return items.map((x) => {
    const y = x + 1;
    return y;
  });
}

const handler = async (e) => {
  await run(e);
  done();
};
