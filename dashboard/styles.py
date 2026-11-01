CSS = '''<style>
:root{color-scheme:dark;--paper:#eee8dc;--muted:#b1b2a4;--line:#41463e;--rust:#e39774;--sage:#a8c7a2;--gold:#d9bc69;--plum:#c4a4cd}
.stApp{background:#242923;color:var(--paper)}
header[data-testid="stHeader"]{background:#242923ed;border-bottom:1px solid var(--line)}
h1,h2,h3{font-family:Georgia,'Times New Roman',serif!important;font-weight:500!important;letter-spacing:-.025em!important;color:var(--paper)}h1{font-size:2.8rem!important}h2{font-size:1.8rem!important}
p,label{letter-spacing:.005em}a{color:var(--rust)}
section[data-testid="stSidebar"]{background:#1b211d;border-right:1px solid #545b4c}
.block-container{padding-top:4.8rem;max-width:1520px;padding-bottom:4rem}
.brand{font-family:Georgia,serif;font-size:1.5rem;padding:5px 0 22px}.brand span{color:var(--rust)}
.eyebrow{font-family:monospace;color:var(--gold);font-size:.72rem;letter-spacing:.15em;text-transform:uppercase;border-left:3px solid var(--rust);padding-left:12px;margin:4px 0 12px}
.statusline{color:var(--muted);font-size:.8rem;padding-bottom:16px;border-bottom:1px solid var(--line)}
[data-testid="stMetric"]{background:#30382e;border:1px solid #56614b;border-top:3px solid var(--sage);padding:18px;border-radius:4px;min-height:112px}
[data-testid="stMetricLabel"]{color:#d1d4c3;font-size:.8rem}[data-testid="stMetricValue"]{font-family:Georgia,serif;font-size:2.05rem!important;color:#f4edd9}
[data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"]{border-top-color:var(--rust);background:#3c302a}
[data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"]{border-top-color:var(--gold);background:#3a3729}
[data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"]{border-top-color:var(--plum);background:#37303c}
button{border-radius:4px!important;font-weight:500!important}button[kind="primary"]{background:#e39774!important;color:#211f1a!important;border-color:#e39774!important}button:hover{border-color:var(--gold)!important}
[data-testid="stExpander"]{background:#272e28;border:1px solid #4b5548;border-radius:4px}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#475043!important;border-radius:6px!important}
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{background:#1f251f!important;border-color:#59614f!important;border-radius:4px!important;color:var(--paper)!important}
.stTabs [data-baseweb="tab-highlight"]{background:var(--rust)}.stTabs [aria-selected="true"]{color:#f1bb94!important}
.hero,.welcome{background:#333a2e;border:1px solid #69735b;border-left:5px solid var(--gold);padding:25px 28px;margin:14px 0 24px;border-radius:5px}
.hero h2,.welcome h2{margin:0}.hero p,.welcome p{color:#c7ccba;max-width:750px;margin:10px 0 0}
.badge{display:inline-block;padding:5px 10px;border:1px solid #826a56;background:#45372c;color:#f3d3ad;border-radius:3px;font-family:monospace;font-size:.72rem}
.taskbar,.compare-summary{padding:18px;background:#2c342c;border:1px solid #58664f;border-radius:5px;margin:12px 0}
.small{color:var(--muted);font-size:.8rem}.section-label,.step-label{font-family:monospace;color:var(--gold);font-size:.8rem;letter-spacing:.06em;text-transform:uppercase;margin:20px 0 12px}
.editor-note{display:flex;justify-content:space-between;gap:20px;background:#e4d9bd;color:#2c3025;padding:18px 22px;margin:12px 0 26px;border-radius:3px}.editor-note b{font-family:monospace;font-size:.8rem}.editor-note span{font-size:.85rem}
.stage-heading{display:flex;align-items:center;gap:15px;padding:4px 0 18px;border-bottom:1px solid #49513f;margin-bottom:14px}.stage-heading>span{font-family:Georgia,serif;font-size:2.2rem;color:var(--rust)}.stage-heading>b{font-family:Georgia,serif;font-size:1.4rem;font-weight:500}.stage-heading small{margin-left:auto;color:var(--gold);font-family:monospace;font-size:.65rem;letter-spacing:.13em}
.nodegrid{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:24px;background:#202720;border:1px solid #555f4d;border-radius:5px}
.node{background:#30382e;border:1px solid #657059;border-radius:5px;padding:18px;min-width:150px;flex:1}.node strong{display:block}.node small{display:block;color:#c2c9b6;font-size:.75rem;margin-top:6px}.node.done{border-color:#9ac290}.node.failed{border-color:#d98779;background:#422e29}.node.active{border-color:var(--gold)}.arrow{color:var(--gold);font-size:1.3rem}
.node-icon{display:inline-grid;place-items:center;width:32px;height:32px;border:1px solid #8c9772;border-radius:50%;background:#414b37;color:#eee2bd;margin-bottom:10px}.node.done .node-icon{color:#c1e5b9}.node.failed .node-icon{color:#ffb2a5;background:#623d31}
.contract-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.contract-row span{background:#3c333f;border:1px solid #7c6881;color:#dfc5e3;padding:5px 9px;font-size:.75rem;border-radius:3px}
.compare-summary>strong{font-family:Georgia,serif;font-size:1.6rem;color:var(--paper)}.compare-summary.failed{background:#3f2b29;border-color:#a56b5e}.compare-summary.recovered{background:#3d3825;border-color:#b39d56}.compare-summary.done{border-color:#8db181}.compare-summary.failed>strong{color:#efad9a}.compare-summary.recovered>strong{color:#e4cd83}.compare-summary.done>strong{color:#b9d8ad}
.compare-facts{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px;font-size:.75rem;color:#bdc4b0}.compare-facts b{display:block;color:#f2e9d9;font-size:.9rem}
.trace-schematic{display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap;margin:20px 0 28px}.stage-route{flex:1;min-width:185px}.evidence-node{background:#30372f;border:1px solid #66715b;border-radius:5px;padding:20px;line-height:1.5}.evidence-node strong{display:block;font-family:Georgia,serif;font-weight:500;font-size:1.2rem;margin:10px 0;color:#f2e9d9}.evidence-node small{display:block;font-size:.78rem;color:#c3cbb7}.evidence-node div{font-size:.9rem}.evidence-node.done{border-top:3px solid #a0c490;background:#2d392d}.evidence-node.failed{border-color:#be8271;border-top:3px solid #df947b;background:#3d2d29}.evidence-node.recovered{border-color:#b39a50;border-top:3px solid #dcc16d;background:#3d3827}.evidence-node.active{border-color:var(--plum);background:#39313e}
.stage-state{float:right;font-family:monospace;font-size:.65rem;letter-spacing:.03em;color:#ded6bb}.failed .stage-state{color:#f3b3a0}.recovered .stage-state{color:#f2d885}.done .stage-state{color:#b9dfa8}.route-arrow{align-self:center;font-size:1.35rem;color:var(--gold)}.recovery-connector{padding:8px 10px;color:#e6cc83;font-size:.8rem}.trace-schematic.vertical{display:block}.vertical .stage-route{width:100%}.vertical .route-arrow{text-align:center;padding:6px}.io-snippet{color:#c2c9b5;font-size:.8rem;margin:14px 0 0!important}.io-snippet b{color:#f0e5c8}
.story{display:flex;gap:12px;padding:18px 0;flex-wrap:wrap}.story-step{flex:1;text-align:center;color:#a6b098;min-width:85px}.story-step span{display:grid;place-items:center;border:1px solid #6b745c;width:38px;height:38px;margin:0 auto 8px;border-radius:50%}.story-step small{display:block}.story-step.done{color:#b6d9a2}.story-step.done span{background:#3f5136;border-color:#9ac184}.story-step.failed{color:#ebb5a1}.story-step.failed span{background:#51352b;border-color:#bd8571}.result-good{border-color:#9fbd86!important}
@media(max-width:800px){.block-container{padding:1rem}.editor-note{display:block}.editor-note span{display:block;margin-top:8px}.nodegrid{padding:12px}.node{min-width:120px}}
</style>'''
