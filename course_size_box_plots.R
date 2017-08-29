
library(ggplot2)
library(scales)      # pairs nicely with ggplot2 for plot label formatting
library(ggthemes)    # has a clean theme for ggplot2
library(RODBC)
library(grid)
library(gridExtra)
library(gtable)
library(lattice)
library(igraph)

SQL_QUERY = "SELECT *
  FROM schedule.Result_ClassSize
WHERE asof = '2016-11-29 15:58:45.000'
ORDER BY COURSE_TITLE;"

# make connection to Data_and_Policy database
conn_info = 'DRIVER={SQL Server};'
conn_info = paste0(conn_info, 'SERVER=WNDWDEVDB;') # server name goes here
conn_info = paste0(conn_info, 'DATABASE=Data_and_Policy;') # database name goes here
conn_info = paste0(conn_info, 'Trusted_Connection=yes') # use windows authentication

# create connection, get data, close connection
dbhandle <- odbcDriverConnect(conn_info)
solution <- sqlQuery(dbhandle, SQL_QUERY, stringsAsFactors=TRUE)
close(dbhandle)


gg = ggplot(solution, aes(Course_type, ClassSize, fill=Course_type))
gg = gg + geom_boxplot(alpha=0.6, outlier.shape = NA) + geom_jitter(width = 0.3, size=1) + stat_boxplot(geom ='errorbar')
gg = gg + scale_y_continuous(limits=c(0,45), breaks = seq(0, 45, by=5)) # max(dataFrame$classSize)
gg = gg + coord_flip()
gg = gg + theme_minimal() + theme(legend.position="bottom", axis.text.y=element_blank())
gg = gg + labs(x="",
               y="Class size",
               title="Model Solution Class Size Distribution",
               fill="Course Category")

gg