# StampFly Workshop Slides — Build Automation
# Usage:
#   make all     — Build everything (tikz + beamer + pptx)
#   make tikz    — TikZ diagrams → PDF → PNG
#   make beamer  — LaTeX Beamer slides → PDF
#   make pptx    — Python-pptx → PPTX
#   make clean   — Remove build artifacts

.PHONY: all tikz beamer pptx clean

# ---------------------------------------------------------------------------
# TikZ diagrams
# ---------------------------------------------------------------------------

TIKZ_DIR   := tikz
IMAGES_DIR := images

TIKZ_SOURCES := $(wildcard $(TIKZ_DIR)/*.tex)
TIKZ_PDFS    := $(TIKZ_SOURCES:.tex=.pdf)
TIKZ_PNGS    := $(patsubst $(TIKZ_DIR)/%.tex,$(IMAGES_DIR)/%.png,$(TIKZ_SOURCES))

tikz: $(TIKZ_PNGS)

$(TIKZ_DIR)/%.pdf: $(TIKZ_DIR)/%.tex
	cd $(TIKZ_DIR) && lualatex -interaction=nonstopmode $(notdir $<)

$(IMAGES_DIR)/%.png: $(TIKZ_DIR)/%.pdf
	@mkdir -p $(IMAGES_DIR)
	sips -s format png -s dpiWidth 288 -s dpiHeight 288 $< --out $@

# ---------------------------------------------------------------------------
# LaTeX Beamer slides
# ---------------------------------------------------------------------------

BEAMER_DIR     := beamer
BEAMER_SOURCES := $(wildcard $(BEAMER_DIR)/lesson_*.tex)
BEAMER_PDFS    := $(BEAMER_SOURCES:.tex=.pdf)

beamer: tikz $(BEAMER_PDFS)

$(BEAMER_DIR)/lesson_%.pdf: $(BEAMER_DIR)/lesson_%.tex $(BEAMER_DIR)/stampfly_slides.sty $(TIKZ_SOURCES)
	cd $(BEAMER_DIR) && lualatex -interaction=nonstopmode $(notdir $<)

# ---------------------------------------------------------------------------
# PowerPoint slides (python-pptx)
# ---------------------------------------------------------------------------

PPTX_SCRIPT := pptx/generate_slides.py
PPTX_OUTPUT := pptx/output

pptx: tikz
	python3 $(PPTX_SCRIPT)

# ---------------------------------------------------------------------------
# All
# ---------------------------------------------------------------------------

all: tikz beamer pptx

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

clean:
	rm -f $(TIKZ_DIR)/*.aux $(TIKZ_DIR)/*.log $(TIKZ_DIR)/*.pdf
	rm -f $(BEAMER_DIR)/*.aux $(BEAMER_DIR)/*.log $(BEAMER_DIR)/*.nav \
	      $(BEAMER_DIR)/*.out $(BEAMER_DIR)/*.snm $(BEAMER_DIR)/*.toc \
	      $(BEAMER_DIR)/*.pdf $(BEAMER_DIR)/*.vrb
	rm -f $(IMAGES_DIR)/*.png
	rm -f $(PPTX_OUTPUT)/*.pptx
