--1
SELECT
	*
FROM
	products;
 
--2
SELECT
	product_name,
	price
FROM
	products;
 
--3
SELECT
	*
FROM
	products
WHERE
	price >= 1000;
 
--4
SELECT
	*
FROM
	products
WHERE
	price >= 1000;
 
--5
SELECT
	*
FROM
	products
WHERE
	product_name LIKE '%ケーブル%';
 
--6
SELECT
	*
FROM
	products
WHERE
	category = 'センサー'
	AND price >= 3000;
 
--7
SELECT
	*
FROM
	products
ORDER BY
	price ASC;
 
--8
SELECT
	*
FROM
	sales
ORDER BY
	quantity DESC;
 
--9
SELECT
	COUNT(*)
FROM
	products;
 
--10
SELECT
	DISTINCT sale_date
FROM
	sales;

--11
SELECT
	SUM(p.price)
FROM
	products p ;
--12
SELECT
	AVG(p.price)
FROM
	products p ;
--13
SELECT
	MAX(s.quantity),
	MIN(s.quantity)
FROM
	sales s ;
--14
SELECT
	s.product_id ,
	SUM(s.quantity) AS amount
FROM
	sales s
GROUP BY
	s.product_id ;
--15
SELECT
	s.product_id ,
	SUM(s.quantity) AS amount
FROM
	sales s
GROUP BY
	s.product_id
ORDER BY
	amount DESC ;
--16
SELECT
	s.product_id ,
	SUM(s.quantity) AS amount
FROM
	sales s
GROUP BY
	s.product_id
HAVING
	amount >= 20
ORDER BY
	amount DESC ;
--17
SELECT
	s.sale_date,
	p.product_name,
	s.quantity
FROM
	sales s
JOIN products p ON
	s.product_id = p.product_id
ORDER BY
	s.sale_date ;
--18
SELECT
	p.product_name,
	s.sale_date
FROM
	products p
LEFT JOIN sales s ON
	p.product_id = s.product_id ;
--19
SELECT
	s.sale_date,
	p.product_name,
	p.price * s.quantity AS amount
FROM
	sales s
JOIN products p ON
	s.product_id = p.product_id ;
--20
SELECT
	p.category,
	SUM(p.price * s.quantity) AS amount
FROM
	products p
JOIN sales s ON
	p.product_id = s.product_id
GROUP BY
	p.category
ORDER BY
	amount DESC ;
--21
SELECT
	p.category || ':' || p.product_name
FROM
	products p;
--22
SELECT
	*
FROM
	products p
WHERE
	LENGTH(p.product_name) >= 8 ;
--23
SELECT
	SUBSTR(s.sale_date, 1, 4) AS YEAR
FROM
	sales s ;
--24
SELECT
	REPLACE(p.product_name, 'センサー', 'Sensor') AS en_name
FROM
	products p ;
--25
SELECT
	*,
	CASE
		WHEN price >= 3000 THEN '高い'
		ELSE '安い'
	END AS price_rank
FROM
	products p ;
--26
SELECT
	*,
	CASE
		WHEN price >= 5000 THEN '高級'
		WHEN price >= 1000 THEN '普通'
		ELSE '格安'
	END AS price_rank
FROM
	products p ;
--27
SELECT
	s.sale_date,
	JULIANDAY(s.sale_date)-JULIANDAY('2023-01-01') AS days_diff
FROM
	sales s ;
--28
SELECT
	STRFTIME('%Y-%m', s.sale_date) AS MONTH,
	SUM(s.quantity) AS total_qty
FROM
	sales s
GROUP BY
	STRFTIME('%Y-%m', s.sale_date);
--29
SELECT
	*
FROM
	products p
ORDER BY
	CASE
		WHEN category = 'スイッチ' THEN 1
		ELSE 2
	END,
	price DESC ;
--30
SELECT
	s.sale_date,
	SUM(
                            s.quantity *
                            CASE
                                          WHEN p.category = 'ケーブル' THEN p.price * 0.9
                                          ELSE p.price
                            END
              ) AS waribikigo
FROM
	sales s
JOIN products p ON
	s.product_id = p.product_id
GROUP BY
	s.sale_date;
--31
SELECT
	*
FROM
	products p
WHERE
	p.category IN ('センサー', 'ネジ');
--32
SELECT
	*
FROM
	products p
WHERE
	p.product_id IN (
	SELECT
		product_id
	FROM
		sales s );
--33
SELECT
	*
FROM
	products p
WHERE
	p.product_id
NOT IN (
	SELECT
		s.product_id
	FROM
		sales s );
--34
SELECT
	p.product_name
FROM
	products p
UNION ALL
SELECT
	p.category
FROM
	products p ;
--35
SELECT
	*
FROM
	products p
WHERE
	p.price <= 2000
UNION
SELECT
	*
FROM
	products p
WHERE
	p.category = 'ケーブル';
--36
SELECT
	*
FROM
	products p
WHERE
	p.price <= 2000
EXCEPT
SELECT
	*
FROM
	products p
WHERE
	p.category = 'ネジ';
--37
SELECT
	*
FROM
	sales s
WHERE
	s.quantity =(
	SELECT
		MAX(s.quantity)
	FROM
		sales s);
--38
SELECT
	*
FROM
	products p
WHERE
	p.price > (
	SELECT
		AVG(p.price)
	FROM
		products p );
--39
CREATE VIEW category_ranking AS
SELECT
	p.category,
	SUM(p.price * s.quantity) AS amount
FROM
	products p
JOIN sales s ON
	p.product_id = s.product_id
GROUP BY
	p.category
ORDER BY
	amount DESC ;
--40
SELECT
	*
FROM
	category_ranking cr
WHERE
	amount >= 10000;