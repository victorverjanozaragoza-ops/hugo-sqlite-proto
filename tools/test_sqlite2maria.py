"""tools/test_sqlite2maria.py — pruebas de las funciones PURAS de sqlite2maria.py.

No hace falta SQLite ni MariaDB: son funciones que reciben datos y devuelven texto.
Ejecuta:  make test   (o: python3 -m unittest discover -s tools -v)
"""
import unittest

from sqlite2maria import EPILOGO, PREAMBULO, ident, insert_lote, literal, lotes, sentencias_tabla, volcado


class TestLiteral(unittest.TestCase):
    def test_nulo_y_numeros(self):
        self.assertEqual(literal(None), "NULL")
        self.assertEqual(literal(42), "42")
        self.assertEqual(literal(True), "1")
        self.assertEqual(literal(2.5), "2.5")

    def test_comilla_simple_se_duplica(self):
        self.assertEqual(literal("O'Brien"), "'O''Brien'")

    def test_barra_invertida_se_escapa(self):
        self.assertEqual(literal("C:\\tmp"), "'C:\\\\tmp'")

    def test_unicode_y_saltos_de_linea_se_conservan(self):
        self.assertEqual(literal("árbol 🔄\nfin"), "'árbol 🔄\nfin'")

    def test_bytes_en_hexadecimal(self):
        self.assertEqual(literal(b"\x00\xff"), "X'00ff'")


class TestIdent(unittest.TestCase):
    def test_comillas_invertidas(self):
        self.assertEqual(ident("groups"), "`groups`")

    def test_comilla_invertida_dentro(self):
        self.assertEqual(ident("a`b"), "`a``b`")


class TestInsert(unittest.TestCase):
    def test_insert_con_dos_filas(self):
        sql = insert_lote("posts", ["id", "clean"], [(1, "hola"), (2, None)])
        self.assertEqual(sql, "INSERT INTO `posts` (`id`, `clean`) VALUES\n(1, 'hola'),\n(2, NULL);\n")

    def test_lotes(self):
        self.assertEqual(lotes([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])
        self.assertEqual(lotes([], 2), [])


class TestVolcado(unittest.TestCase):
    def test_vacia_antes_de_insertar(self):
        sentencias = sentencias_tabla("posts", ["id"], [(1,), (2,), (3,)], tamano=2)
        self.assertEqual(sentencias[0], "DELETE FROM `posts`;\n")
        self.assertEqual(len(sentencias), 3)  # DELETE + 2 lotes

    def test_tabla_vacia_solo_hace_delete(self):
        self.assertEqual(sentencias_tabla("pages", ["id"], []), ["DELETE FROM `pages`;\n"])

    def test_volcado_completo(self):
        sql = volcado([("groups", ["id", "name"], [(1, "Admin")])])
        self.assertTrue(sql.startswith(PREAMBULO))
        self.assertTrue(sql.endswith(EPILOGO))
        self.assertIn("SET NAMES utf8mb4;", sql)
        self.assertIn("INSERT INTO `groups` (`id`, `name`) VALUES\n(1, 'Admin');", sql)

    def test_es_pura(self):
        tablas = [("groups", ["id"], [(1,), (2,)])]
        self.assertEqual(volcado(tablas), volcado(tablas))
        self.assertEqual(tablas, [("groups", ["id"], [(1,), (2,)])])


if __name__ == "__main__":
    unittest.main()
