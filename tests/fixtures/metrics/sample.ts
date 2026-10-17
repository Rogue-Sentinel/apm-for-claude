class Users {
  async fetch(id: string): Promise<User> {
    return get(id);
  }
}
