from activity_browser.bwutils.superstructure.graph_traversal import GraphTraversal
from bw2data import Database, Method, databases


def init_database():
    biosphere = Database("biosphere")
    biosphere.register()
    biosphere.write({
        ("biosphere", "CO2"): {
            'categories': ['things'],
            'exchanges': [],
            'name': 'an emission',
            'type': 'emission',
            'unit': 'kg'
        }})

    db = Database("test")
    db.register()
    db.write({
        ("test", "A"): {
            'name': 'A',
            'exchanges': [
                {'input': ("test", "A"), 'amount': -1.0, 'type': 'production'},
                {'input': ("test", "B"), 'amount': -1.0, 'type': 'technosphere'}
            ]
        },
        ("test", "B"): {
            'name': 'B',
            'exchanges': [
                {'input': ("test", "B"), 'amount': -2.0, 'type': 'production'},
                {'input': ("test", "C"), 'amount': 1.0, 'type': 'technosphere'}]},
        ("test", "C"): {
            'name': 'C',
            'exchanges': [
                {'input': ("test", "C"), 'amount': 1.0, 'type': 'production'},
                {'input': ("test", "D"), 'amount': -1.0, 'type': 'technosphere'}
            ]
        },
        ("test", "D"): {
            'name': 'D',
            'exchanges': [
                {'input': ("test", "D"), 'amount': -1.0, 'type': 'production'},
                {'input': ('biosphere', 'CO2'), 'amount': -1.0, 'type': 'biosphere'}
            ]
        },
    })

    method = Method(("a method",))
    method.register()
    method.write([(("biosphere", "CO2"), 1)])

    return db, biosphere, method


def delete_database():
    del databases['test']
    del databases['biosphere']
    Method(("a method",)).deregister()

def test_single_activity_graph_traversal():
    nodes_expected = {
        -1: {'amount': 1, 'cum': -0.5, 'ind': 0},
        ('test', 'C'): {'amount': 0.5, 'cum': -0.5, 'ind': 0},
        ('test', 'D'): {'amount': -0.5, 'cum': -0.5, 'ind': 0},
        ('biosphere', 'CO2'): {'amount': -0.5, 'cum': -0.5, 'ind': -0.5},
        ('test', 'A'): {'amount': -1.0, 'cum': -0.5, 'ind': 0},
        ('test', 'B'): {'amount': -1.0, 'cum': -0.5, 'ind': 0}
    }
    edges_expected = [
        {'to': -1, 'from': ('test', 'A'), 'amount': -1, 'exc_amount': -1, 'impact': -0.5},
        {'to': ('test', 'A'), 'from': ('test', 'B'), 'amount': -1.0, 'exc_amount': 1.0, 'impact': -0.5},
        {'to': ('test', 'B'), 'from': ('test', 'C'), 'amount': 0.5, 'exc_amount': -0.5, 'impact': -0.5},
        {'to': ('test', 'C'), 'from': ('test', 'D'), 'amount': -0.5, 'exc_amount': -1.0, 'impact': -0.5},
        {'to': ('test', 'D'), 'from': ('biosphere', 'CO2'), 'amount': -0.5, 'exc_amount': 1.0, 'impact': -0.5}
    ]

    act = [a for a in Database("test") if a._data["name"] == "A"][0]
    demand = {act: -1}

    gt = GraphTraversal(use_keys=True, include_biosphere=True, importance_first=True)
    actual = gt.calculate(demand, ("a method",))
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected

    # test depth first traversal
    gt.traverse = gt.traverse_depth_first
    actual = gt.calculate(demand, ("a method",))
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected

    # test include_biosphere = False
    gt.traverse = gt.traverse_importance_first
    gt.include_biosphere = False
    actual = gt.calculate(demand, ("a method",))
    nodes_expected = {k: v for k, v in nodes_expected.items() if k == -1 or k[0] != "biosphere"}
    nodes_expected[("test", "D")]["ind"] = -0.5
    edges_expected = [e for e in edges_expected if e["from"] == -1 or e["from"][0] != "biosphere"]
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected

    # test use_keys = False
    gt.use_keys = False
    actual = gt.calculate(demand, ("a method",))
    nodes_expected = {gt.lca.activity_dict.get(k, -1): v for k, v in nodes_expected.items()}
    for e in edges_expected:
        e["to"] = gt.lca.activity_dict.get(e["to"], -1)
        e["from"] = gt.lca.activity_dict.get(e["from"], -1)
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected


def test_multi_activity_graph_traversal():
    nodes_expected = {
        -1: {'amount': 1, 'cum': -1.5, 'ind': 0},
        ('test', 'C'): {'amount': 0.5, 'cum': -0.5, 'ind': 0},
        ('test', 'D'): {'amount': -1.5, 'cum': -1.5, 'ind': 0},
        ('biosphere', 'CO2'): {'amount': -1.5, 'cum': -1.5, 'ind': -1.5},
        ('test', 'A'): {'amount': -1.0, 'cum': -0.5, 'ind': 0},
        ('test', 'B'): {'amount': -1.0, 'cum': -0.5, 'ind': 0}
    }
    edges_expected = [
        {'to': -1, 'from': ('test', 'A'), 'amount': -1, 'exc_amount': -1, 'impact': -0.5},
        {'to': -1, 'from': ('test', 'D'), 'amount': -1, 'exc_amount': -1, 'impact': -1.0},
        {'to': ('test', 'A'), 'from': ('test', 'B'), 'amount': -1.0, 'exc_amount': 1.0, 'impact': -0.5},
        {'to': ('test', 'B'), 'from': ('test', 'C'), 'amount': 0.5, 'exc_amount': -0.5, 'impact': -0.5},
        {'to': ('test', 'C'), 'from': ('test', 'D'), 'amount': -0.5, 'exc_amount': -1.0, 'impact': -0.5},
        {'to': ('test', 'D'), 'from': ('biosphere', 'CO2'), 'amount': -0.5, 'exc_amount': 1.0, 'impact': -0.5},
        {'to': ('test', 'D'), 'from': ('biosphere', 'CO2'), 'amount': -1.0, 'exc_amount': 1.0, 'impact': -1.0}
    ]

    A = [a for a in Database("test") if a._data["name"] == "A"][0]
    D = [a for a in Database("test") if a._data["name"] == "D"][0]
    demand = {A: -1, D:-1}

    gt = GraphTraversal(use_keys=True, include_biosphere=True, importance_first=True)
    actual = gt.calculate(demand, ("a method",))
    assert actual["nodes"] == nodes_expected
    assert actual["edges"] == edges_expected

    return


if __name__ == "__main__":
    init_database()
    test_single_activity_graph_traversal()
    test_multi_activity_graph_traversal()
    delete_database()
    pass
