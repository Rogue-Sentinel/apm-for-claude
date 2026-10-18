from apm.metrics import Report, measure_text


def _classes(text: str, path: str = "a.hpp") -> list[tuple[str, int, int]]:
    metric = measure_text(path, text)
    return [(c.name, c.line, c.public_methods) for c in metric.classes]


def _struct_count(*members: str) -> int:
    body = "\n".join(members)
    [(_, _, count)] = _classes(f"struct A {{\n{body}\n}};\n")
    return count


def test_methods_after_public_are_counted_and_private_ones_are_not() -> None:
    text = "class A {\npublic:\nvoid a();\nvoid b();\nprivate:\nvoid c();\n};\n"

    assert _classes(text) == [("A", 1, 2)]


def test_a_class_starts_private_and_a_struct_or_union_starts_public() -> None:
    text = "class A { void a(); };\nstruct S { void a(); };\nunion U { void a(); };\n"

    assert _classes(text) == [("A", 1, 0), ("S", 2, 1), ("U", 3, 1)]


def test_protected_methods_are_not_public() -> None:
    assert _classes("struct S {\nprotected:\nvoid a();\n};\n") == [("S", 1, 0)]


def test_constructors_destructors_and_deleted_members_are_not_counted() -> None:
    members = ("A();", "explicit A(int);", "A(const A&) = delete;", "A(A&&) = default;",
               "virtual ~A();", "void f() = delete;")

    assert _struct_count(*members) == 0


def test_operators_including_defaulted_assignment_are_counted() -> None:
    members = ("A& operator=(A&&) noexcept;", "A& operator=(const A&) = default;",
               "bool operator==(const A&) const;", "explicit operator bool() const;")

    assert _struct_count(*members) == 4


def test_static_virtual_pure_inline_and_template_methods_are_counted() -> None:
    members = ("static A make();", "virtual void v() = 0;", "int get() const { return x_; }",
               "template <typename T> void visit(T t) { t(); }",
               "[[nodiscard]] auto size() const -> int;")

    assert _struct_count(*members) == 5


def test_data_members_and_declarations_that_are_not_methods() -> None:
    members = ("int x = compute();", "int y{0};", "std::function<void()> cb;", "void (*fp)(int);",
               "using Base::Base;", "friend void swap(A&, A&);", "typedef int T;",
               "enum class Mode { On, Off };", "static_assert(sizeof(int) == 4);")

    assert _struct_count(*members) == 0


def test_nested_classes_are_counted_on_their_own() -> None:
    text = "struct Outer {\nvoid a();\nstruct Inner {\nvoid b();\nvoid c();\n};\n};\n"

    assert _classes(text) == [("Outer", 1, 1), ("Outer::Inner", 3, 2)]


def test_forward_declarations_and_out_of_class_definitions_are_not_classes() -> None:
    assert _classes("class A;\nvoid A::f() {\n}\n") == []


def test_templates_attributes_bases_and_final_are_read_from_the_head() -> None:
    text = ("template <typename T>\nclass [[nodiscard]] Box final : public Base<T>, private Other {\n"
            "public:\nvoid a();\n};\n")

    assert _classes(text) == [("Box", 2, 1)]
    assert _classes("struct alignas(16) V { void a(); };\n") == [("V", 1, 1)]


def test_namespaces_and_extern_c_blocks_are_transparent() -> None:
    text = 'namespace va::ui {\nextern "C" {\nstruct S { void a(); };\n}\n}\n'

    assert _classes(text) == [("S", 3, 1)]


def test_classes_inside_function_bodies_and_struct_initializers_are_not_reported() -> None:
    text = "void f() {\nstruct L { void a(); };\n}\nstruct Point p = {1, 2};\n"

    assert _classes(text) == []


def test_access_labels_and_bitfields_and_constructor_initializers_do_not_confuse_the_count() -> None:
    text = ("class A {\npublic:\nA() : x_(1), y_{2} {}\nint bits : 3;\nvoid a();\n"
            "private:\nint x_, y_;\n};\n")

    assert _classes(text) == [("A", 1, 1)]


DATABASE = """class Database {
public:
    enum class Mode { ReadWrite, ReadOnly };
    explicit Database(const std::string& path, Mode mode = Mode::ReadWrite);
    ~Database();
    Database(const Database&) = delete;
    Database& operator=(const Database&) = delete;
    Database(Database&& other) noexcept;
    Database& operator=(Database&& other) noexcept;
    void exec(std::string_view sql);
    [[nodiscard]] Statement prepare(std::string_view sql);
    std::string query_string(std::string_view sql);
    int query_int(std::string_view sql);
    [[nodiscard]] sqlite3* handle() const noexcept { return db_; }
    [[nodiscard]] int changes() const noexcept;
private:
    sqlite3* db_{nullptr};
};
"""

MAP_SCREEN = """namespace va::ui {
class MapScreen {
public:
    explicit MapScreen(Config& config);
    void show_flight(const Flight& flight);
    const Flight* flight() const;
    void draw(ImVec2 size);
    bool leave();
    std::vector<TileId> tiles_needed() const;
    void upload_tile(TileId id, const Pixels& pixels);
    void set_basemap_failed(bool failed);
    std::size_t resident_tile_bytes() const;
private:
    struct Canvas { ImVec2 origin; float width{}; };
    void draw_basemap(const Canvas& canvas);
    void draw_route(const Canvas& canvas,
                    const Route& route);
    Canvas canvas_{};
};
}
"""


def test_the_xp12_database_header_has_seven_public_methods() -> None:
    assert _classes(DATABASE) == [("Database", 1, 7)]


def test_the_xp12_map_screen_header_has_eight_public_methods() -> None:
    assert _classes(MAP_SCREEN) == [("MapScreen", 2, 8), ("MapScreen::Canvas", 14, 0)]


def test_a_cpp_file_with_unbalanced_braces_reports_no_classes() -> None:
    metric = measure_text("a.hpp", "class A {\npublic:\nvoid a();\n")

    assert (metric.functions_measured, metric.classes) == (False, ())


def test_c_files_are_not_scanned_for_classes() -> None:
    assert measure_text("a.c", "struct S { int a; };\n").classes == ()


def test_cpp_files_no_longer_count_as_class_unmeasured() -> None:
    report = Report((measure_text("a.hpp", "struct S { void a(); };\n"),))

    assert report.classes_unscanned() == {}
